from fastapi import APIRouter, Depends
from typing_extensions import Union

from app.functions.data import DataRepository
from app.models.transactions import Basket, Response, EnrichedBasket
from ..database import database
from ..functions.transactions import paymentHandlerFactory, PaymentHandler

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
		)
):
	"""
	Submit a checkout request
	:param basket: The basket to checkout
	:param deliveryDetails: The delivery details
	:param paymentHandler: The payment handler to use. Determined by the user's payment method.
	:return:
	"""
	pass
