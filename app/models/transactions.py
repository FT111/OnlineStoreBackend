from abc import ABC, abstractmethod
from enum import Enum
from typing import Union

from pydantic import BaseModel, Field, field_validator

from app.models.listings import SKU
from app.models.response import ResponseSchema
from app.models.users import PrivilegedUser


class Basket(BaseModel):
	"""
	A collection of SKU ids and their quantities.
	"""
	items: dict[str, dict[str, Union[str, int]]] = Field(description='A dictionary of SKUs with their selected quantities',
														 examples=["{'SKU_ID': {'quantity': 1}}"])

	@field_validator('items')
	def validate_items(cls, value):
		if len(value) < 1:
			raise ValueError('Basket must contain at least one SKU')

		for sku in value:
			if 'quantity' not in value[sku]:
				raise ValueError('SKU quantities must be specified')

			if value[sku]['quantity'] < 1:
				raise ValueError('SKU quantities must be greater than 0')

		return value


class EnrichedBasket(Basket):
	"""
	A basket is a collection of listings
	"""
	items: dict[str, dict] = Field(description="""A dictionary of full SKU objects with 
																	their selected quantities and parent listings""",
								   examples=['''{'SKU_ID': {'quantity': 1,
																						'sku': SKU,
																						'listing': Listing}}'''])


class PaymentDetails(ABC, BaseModel):
	"""
	Details for a payment
	"""

	@abstractmethod
	def __repr__(self):
		"""
		The string representation of the payment method
		Uses a model method to prevent user input from being used directly
		:return:
		"""
		pass


class CardPaymentDetails(PaymentDetails):
	"""
	Details for a card payment
	"""
	cardNumber: str = Field(description='The card number')
	cardExpiration: str = Field(description='The card expiry date')
	cardCVV: str = Field(description='The card CVV')
	cardHolder: str = Field(description='The card holder name')

	def __repr__(self):
		return 'card'


class Checkout(BaseModel):
	"""
	A full purchase
	"""

	basket: EnrichedBasket = Field(description='The basket to purchase')
	user: PrivilegedUser = Field(description='The user making the purchase')
	payment: Union[
		CardPaymentDetails
	] = Field(description='The payment method')


class Order(BaseModel):
	"""
	An order of a single SKU.
	"""

	sku: SKU = Field(description='The SKU being ordered')
	quantity: int = Field(description='The quantity of the SKU being ordered')
	value: int = Field(description='The total value of the order, in pence')
	status: Enum = Field(description='The status of the order')
	recipient: PrivilegedUser = Field(description='The recipient of the order')
	seller: PrivilegedUser = Field(description='The seller of the order')


class Response:
	class BasketMeta(BaseModel):
		"""
		Metadata for a basket response
		"""
		total: int = Field('The total number of items in the basket',
						   examples=[1])
		value: int = Field('The total value of the basket, in pence',
						   examples=[1])

	class EnrichedBasketResponse(ResponseSchema[BasketMeta, EnrichedBasket]):
		"""
		A response containing an enriched basket
		"""
		pass
