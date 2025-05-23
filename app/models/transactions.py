import dataclasses
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Union

from pydantic import BaseModel, Field, field_validator
from typing_extensions import Optional, Dict, List

from app.models.listings import SKU, ShortListing
from app.models.response import ResponseSchema
from app.models.users import PrivilegedUser, User


class Basket(BaseModel):
	"""
	A collection of SKU ids and their quantities.
	"""
	items: Dict[str, Dict[str, Union[str, int]]] = Field(
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
	items: Dict[str, dict] = Field(description="""A dictionary of full SKU objects with 
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

	@field_validator('cardNumber')
	def validateCardNumber(cls, value):
		"""
		Validate the card number
		Checks through Luhn and length
		:param value:
		:return:
		"""

		if len(value) < 14 or len(value) > 19:
			raise ValueError('Card number must be between 14 and 19 characters')

		# Luhn algorithm
		checksum = 0
		# Loop through in reverse
		for i, digit in enumerate(value[::-1]):
			if i % 2 == 0:
				checksum += int(digit)
			else:
				checksum += sum([int(x) for x in str(int(digit) * 2)])

		# Error if the checksum is not a multiple of ten
		if checksum % 10 != 0:
			raise ValueError('Invalid card number')

		return value


class DeliveryDetails(BaseModel):
	"""
	Details for delivery
	"""
	addressLine1: str = Field(description='The first line of the address')
	addressLine2: Optional[str] = Field(description='The second line of the address')
	city: str = Field(description='The city')
	postcode: str = Field(description='The postcode')
	country: str = Field(description='The country')
	saveAddress: Optional[bool] = Field(False, description='Whether to save the address for future use')

	@field_validator('postcode')
	def validatePostcode(cls, value):
		if len(value) < 1:
			raise ValueError('Postcode must not be empty')

		if len(value) < 5 or len(value) > 7:
			raise ValueError('Postcode must be between 5 and 7 characters')

		return value


@dataclasses.dataclass
class SKUPurchase:
	"""
	A purchase of an individual SKU
	"""
	sku: SKU
	listing: Optional[ShortListing]
	quantity: int
	value: int


@dataclasses.dataclass
class InternalPurchase:
	"""
	A parent purchase
	"""

	id: str
	user: PrivilegedUser
	deliveryDetails: DeliveryDetails
	addedAt: int


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
	skus: List[SKUPurchase] = Field(description='The SKUs in the order')
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
	skus: List[SKUPurchase]
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
	purchases: List[Order] = Field(description='The user\'s orders')
	sales: List[Order] = Field(description='The user\'s sales')


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

	class CheckoutResponse(ResponseSchema[CheckoutMeta, List[Order]]):
		"""
		A response containing a completed purchase
		"""
		pass

	class OrderResponse(ResponseSchema[OrderMeta, Order]):
		"""
		A response containing an order
		"""
		pass
