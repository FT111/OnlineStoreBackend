import time
import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from typing_extensions import Union

from app.functions.data import DataRepository
from app.models.transactions import Basket, Response, EnrichedBasket, Order, OrderStatuses, SKUPurchase, InternalOrder
from .. import constants
from ..database import database
from ..functions.auth import userRequired
from ..functions.transactions import paymentHandlerFactory, PaymentHandler
from ..models.listings import SKUWithUser

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
		deliveryDetails: dict,
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

	print(basket)
	print(deliveryDetails)

	# First – validate the basket
	# Second – validate the delivery details
	# Third – make the payment
	# Fourth – add the order to the database
	# Fifth – update the stock of the SKUs in listings

	skus: list[SKUWithUser] = data.idsToSKUs(basket.items.keys(), SKUWithUser)
	user = data.getUserByID(user['id'])

	purchaseID = str(uuid.uuid4())

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


@router.put('/{orderID}', response_model=Response.OrderResponse)
def updateOrder(
		orderID: str,
		updatedOrder: Order,
		user=Depends(userRequired)
):
	"""
	Update an order.
	Recipients can update to CANCELLED, sellers can update to any status.
	:param orderID: The ID of the order to update
	:param updatedOrder: The updated order
	:param user: The user updating the order
	:return:
	"""

	data = DataRepository(database.db)

	order = data.getOrderByID(orderID)

	if not order:
		raise HTTPException(404, f"Order {orderID} not found")

	if order.seller.id != user['id']:
		if updatedOrder.status != OrderStatuses.CANCELLED or order.recipient.id != user['id']:
			raise HTTPException(403, "You do not have permission to update this order")

	if order.status == OrderStatuses.CANCELLED:
		raise HTTPException(409, "Order is cancelled and cannot be updated")

	data.updateOrderStatus(orderID, updatedOrder.status)

	return Response.OrderResponse(
		meta={},
		data=updatedOrder
	)
