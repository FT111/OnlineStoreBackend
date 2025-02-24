import dataclasses
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Union

from pydantic import BaseModel, Field, field_validator
from typing_extensions import Optional

from app.models.listings import SKU, ShortListing
from app.models.response import ResponseSchema
from app.models.users import PrivilegedUser, User


class Basket(BaseModel):
	"""
	A collection of SKU ids and their quantities.
	"""
	items: dict[str, dict[str, Union[str, int]]] = Field(
		description='A dictionary of SKUs with their selected quantities',
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


@dataclasses.dataclass
class SKUPurchase:
	"""
	A purchase of an individual SKU
	"""
	sku: SKU
	listing: Optional[ShortListing]
	quantity: int
	value: int


class Checkout(BaseModel):
	"""
	A full purchase
	"""

	basket: EnrichedBasket = Field(description='The basket to purchase')
	user: PrivilegedUser = Field(description='The user making the purchase')
	payment: Union[
		CardPaymentDetails
	] = Field(description='The payment method')


@dataclasses.dataclass
class InternalCheckout:
	"""
	A full purchase
	"""

	basket: EnrichedBasket
	user: PrivilegedUser
	payment: Union[
		CardPaymentDetails
	]


class OrderStatuses(str, Enum):
	"""
	Different possible statuses for an order
	"""
	PROCESSING = 'Processing'
	DISPATCHED = 'Dispatched'
	OUT_FOR_DELIVERY = 'Out for delivery'
	DELIVERED = 'Delivered'
	CANCELLED = 'Cancelled'


class Order(BaseModel):
	"""
	An order of a single SKU.
	"""

	id: str = Field(description='The unique ID of the order')
	skus: list[SKUPurchase] = Field(description='The SKUs in the order')
	value: int = Field(description='The total value of the order, in pence')
	status: OrderStatuses = Field(description='The status of the order', examples=[OrderStatuses.PROCESSING])
	recipient: Optional[PrivilegedUser] = Field(description='The recipient user of the order')
	seller: Optional[User] = Field(description='The user fulfilling the order')
	addedAt: int = Field(description='The date the order was added')
	updatedAt: int = Field(description='The date the order was last updated')
	purchaseID: str = Field(description='The ID of the purchase that the order is part of')


class InternalOrder(BaseModel):
	"""
	An order of a single SKU.
	"""

	id: str
	skus: list[SKUPurchase]
	value: int
	status: OrderStatuses
	seller: User
	recipient: User
	addedAt: int
	updatedAt: int
	purchaseID: str


class UserOrders(BaseModel):
	"""
	A user's orders
	"""
	purchases: list[Order] = Field(description='The user\'s orders')
	sales: list[Order] = Field(description='The user\'s sales')


class Response:
	class OrderMeta(BaseModel):
		"""
		Metadata for an order response
		"""
		pass

	class BasketMeta(BaseModel):
		"""
		Metadata for a basket response
		"""
		total: int = Field('The total number of items in the basket',
						   examples=[1])
		value: int = Field('The total value of the basket, in pence',
						   examples=[1])

	class CheckoutMeta(BaseModel):
		"""
		Metadata for a checkout response
		"""
		purchaseID: str = Field('The ID of the completed purchase', examples=[str(uuid.uuid4())])

	class EnrichedBasketResponse(ResponseSchema[BasketMeta, EnrichedBasket]):
		"""
		A response containing an enriched basket
		"""
		pass

	class CheckoutResponse(ResponseSchema[CheckoutMeta, list[Order]]):
		"""
		A response containing a completed purchase
		"""
		pass

	class OrderResponse(ResponseSchema[OrderMeta, Order]):
		"""
		A response containing an order
		"""
		pass
