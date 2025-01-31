from typing import Union

from pydantic import BaseModel, Field, field_validator

from app.models.response import ResponseSchema


class Basket(BaseModel):
	"""
	A collection of SKU ids and their quantities.
	"""
	items: dict[str, dict[str, Union[str, int]]] = Field('A dictionary of SKUs with their selected quantities',
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
	items: dict[str, dict] = Field("""A dictionary of full SKU objects with 
																	their selected quantities and parent listings""",
								   examples=['''{'SKU_ID': {'quantity': 1,
																						'sku': SKU,
																						'listing': Listing}}'''])


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
