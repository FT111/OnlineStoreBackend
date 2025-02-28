from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.response import ResponseSchema


class Attribute(BaseModel):
	pass


class SubCategory(BaseModel):
	"""
	SubCategory Model
	"""

	id: int = Field(..., title="SubCategory ID", description="The ID of the subcategory")
	title: str = Field(..., title="SubCategory Title", description="The title of the subcategory")

	@classmethod
	@field_validator("title")
	def validate_title(cls, value):
		if len(value) < 3:
			raise ValueError('Title must be at least 3 characters long')
		return value


class Category(BaseModel):
	"""
	Category Model
	"""
	id: int = Field(..., title="Category ID", description="The ID of the category")
	title: str = Field(..., title="Category Title", description="The title of the category")
	description: str = Field(..., title="Category Description", description="The description of the category")
	colour: str = Field(..., title="Category Colour", description="The RGB colour value of the category")

	subCategories: Optional[List[SubCategory]] = Field(None, title="Subcategories",
													   description="The subcategories of the category")

	@classmethod
	@field_validator("title")
	def validate_title(cls, value):
		if len(value) < 3:
			raise ValueError('Title must be at least 3 characters long')
		return value

	@classmethod
	@field_validator("description")
	def validate_description(cls, value):
		if len(value) < 3:
			raise ValueError('Description must be at least 3 characters long')
		return value

	@classmethod
	@field_validator("colour")
	def validate_colour(cls, value):
		if len(value) != 6:
			raise ValueError('Colour must be a 6 character hex code')
		return value


class Response:
	"""
	Response Models
	"""

	class CategoryMeta(BaseModel):
		pass

	class CategoriesMeta(BaseModel):
		total: int = Field(..., title="Total Categories", description="The total number of categories")

	class Category(ResponseSchema[CategoryMeta, Category]):
		"""
		Category Response Model
		"""
		pass

	class Categories(ResponseSchema[CategoriesMeta, list]):
		"""
		Response Model for multiple categories
		"""
		pass
