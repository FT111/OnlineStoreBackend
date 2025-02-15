from fastapi import APIRouter, Depends, HTTPException
from typing_extensions import Union

from app.functions.data import DataRepository
from app.models.transactions import Basket, Response, EnrichedBasket
from ..database import database
from ..functions.transactions import paymentHandlerFactory, PaymentHandler
from ..models.listings import SKUWithStock

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
		paymentDetails: PaymentHandler = Depends(
			paymentHandlerFactory
		)
):
	"""
	Submit a checkout request
	:param basket: The basket to checkout
	:param deliveryDetails: The delivery details
	:param paymentDetails: The payment handler to use. Determined by the user's payment method.
	:return:
	"""

	data = DataRepository(database.db)

	print(basket)
	print(deliveryDetails)

	# First – validate the basket
	# Second – validate the delivery details
	# Third – make the payment
	# Fourth – add the order to the database

	skus: list[SKUWithStock] = data.idsToSKUs(basket.items.keys(), SKUWithStock)
	skusWithQuantities = []
	totalValue = 0
	for sku in skus:
		# Guard clause - Check the stock of the SKU
		if sku.stock < basket.items[sku.id]['quantity']:
			raise HTTPException(409, f"SKU vali{sku.id} has insufficient stock")

		skusWithQuantities.append({
			'sku': sku,
			'quantity': basket.items[sku.id]['quantity'],
			'value': sku.price * basket.items[sku.id]['quantity']
		})
		totalValue += sku.price * basket.items[sku.id]['quantity']

