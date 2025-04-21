import time
import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from starlette.requests import Request
from typing_extensions import Union

from app.functions.data import DataRepository
from app.models.transactions import Basket, Response, EnrichedBasket, Order, OrderStatuses, SKUPurchase, InternalOrder, \
	DeliveryDetails, InternalPurchase
from .. import constants
from ..database import database
from ..functions.auth import userRequired
from ..functions.transactions import paymentHandlerFactory, PaymentHandler
from ..instances import emailService, rateLimiter
from ..models.emails import Templates
from ..models.listings import SKUWithUser
from ..models.users import PrivilegedUser

router = APIRouter(prefix="/transactions", tags=["Transactions", "Sales"])


@router.post('/basket/enrich', response_model=Response.EnrichedBasketResponse)
async def enrichBasket(
		basket: Union[Basket, EnrichedBasket],
):
	"""
	Enrich a basket with associated SKUs and listings
	:param basket: The basket to enrich
	:return: The enriched basket
	"""

	data = DataRepository(database.db)

	enrichedBasket = data.enrichBasket(basket)

	return Response.EnrichedBasketResponse(meta={
		'total': sum([item['quantity'] for item in enrichedBasket.items.values()]),
		'value': sum([item['quantity'] * item['sku'].price for item in enrichedBasket.items.values()])
	},
		data=enrichedBasket
	)


@router.post('/checkout')
def submitCheckout(
		basket: EnrichedBasket,
		deliveryDetails: DeliveryDetails,
		paymentHandler: PaymentHandler = Depends(
			paymentHandlerFactory
		),
		user=Depends(userRequired)
):
	"""
	Submit a checkout request
	:param basket: The basket to checkout
	:param deliveryDetails: The delivery details
	:param paymentHandler: The payment handler to use. Determined by the user's payment method.
	:param user: The user submitting the checkout request. Fetched from the request state.
	:return:
	"""

	data = DataRepository(database.db)

	# First – validate the basket
	# Second – validate the delivery details
	# Third – make the payment
	# Fourth – add the order to the database
	# Fifth – update the stock of the SKUs in listings

	skus: list[SKUWithUser] = data.idsToSKUs(basket.items.keys(), SKUWithUser)
	user: PrivilegedUser = data.getUserByID(user['id'],
							requestUser=user,
							includePrivileged=True)  # Fetch the user from the database to ensure the user is valid
	purchaseID = str(uuid.uuid4())
	purchase = InternalPurchase(
		id=purchaseID,
		user=user,
		deliveryDetails=deliveryDetails,
		addedAt=int(time.time())
	)

	if deliveryDetails.saveAddress is True:
		user.addressLine1 = deliveryDetails.addressLine1
		user.addressLine2 = deliveryDetails.addressLine2
		user.city = deliveryDetails.city
		user.postcode = deliveryDetails.postcode
		user.country = deliveryDetails.country
		data.updateUser(user)


	totalValue = 0
	ordersPerSeller = defaultdict(list)
	for sku in skus:
		# Guard clause - Check the stock of the SKU
		if sku.stock < basket.items[sku.id]['quantity']:
			raise HTTPException(409, f"SKU {sku.id} has insufficient stock")

		# Add the value of the purchased SKU quantity to the total value
		totalValue += sku.price * basket.items[sku.id]['quantity']

		ordersPerSeller[sku.ownerUser.id].append(SKUPurchase(
			sku=sku,
			listing=None,
			quantity=basket.items[sku.id]['quantity'],
			value=sku.price * basket.items[sku.id]['quantity']
		))

	paymentHandler.makePayment(totalValue, constants.EBUY_IBAN)

	data.addPurchase(purchase)

	# Add the orders to the database
	orders = []
	for seller, products in ordersPerSeller.items():
		order = InternalOrder(
			id=str(uuid.uuid4()),
			skus=products,
			value=sum([order.value for order in products]),
			status=OrderStatuses.PROCESSING,
			seller=products[0].sku.ownerUser,
			recipient=user,
			addedAt=int(time.time()),
			updatedAt=int(time.time()),
			purchaseID=purchaseID

		)
		orders.append(Order(**dict(order)))
		data.addOrder(order)

	# Update the stock of the SKUs
	for sku in skus:
		data.updateSKUStock(sku.id, sku.stock - basket.items[sku.id]['quantity'])

	return Response.CheckoutResponse(
		meta={
			"purchaseID": purchaseID
		},
		data=orders
	)


@rateLimiter.limit("1/minute")
@router.put('/{orderID}', response_model=Response.OrderResponse)
def updateOrder(
		orderID: str,
		updatedOrder: Order,
		backgroundsTasks: BackgroundTasks,
		user=Depends(userRequired),
		request=Request,
):
	"""
	Update an order.
	Recipients can update to CANCELLED, sellers can update to any status.
	:param backgroundsTasks:
	:param request: HTTP request object
	:param orderID: The ID of the order to update
	:param updatedOrder: The updated order
	:param user: The user updating the order
	:return:
	"""

	data = DataRepository(database.db)
	existingOrder = data.getOrderByID(orderID)

	if not existingOrder:
		raise HTTPException(404, f"Order {orderID} not found")

	if existingOrder.seller.id != user['id']:
		# The recipient can only cancel the order
		if updatedOrder.status != OrderStatuses.CANCELLED or existingOrder.recipient.id != user['id']:
			raise HTTPException(403, "You do not have permission to update this order")

	if existingOrder.status == OrderStatuses.CANCELLED:
		raise HTTPException(409, "Order is cancelled and cannot be updated")

	data.updateOrderStatus(existingOrder, updatedOrder.status)

	existingOrder.status = updatedOrder.status

	# Send an email to the order recipient in the background
	def sendOrderUpdateEmail():
		emailService.sendEmailTemplate(
			**dict(existingOrder),
			template=Templates.OrderUpdateEmail(),
			recipientAddress=existingOrder.recipient.emailAddress,
		)
	backgroundsTasks.add_task(sendOrderUpdateEmail)

	return Response.OrderResponse(
		meta={},
		data=updatedOrder
	)
