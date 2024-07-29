from pydantic import BaseModel, Field, EmailStr, model_validator, HttpUrl, field_validator
from typing import List, Optional, Union, Dict, Any, Tuple, Set
from typing_extensions import Annotated

from app.models.users import User, PrivilegedUser, DatabaseUser
from app.models.response import ResponseSchema


class SKU(BaseModel):
    """
    Product SKU/Variant
    """
    id: str = Field(..., title="Product SKU", description="The SKU of the product")
    title: str = Field(..., title="Product Title", description="The title of the product SKU", max_length=50)
    description: str = Field(..., title="Product Description",
                             description="The short description of the product SKU", max_length=50)
    images: Optional[List[str]] = Field(..., title="Product Images", description="The images of the product SKU")
    price: float = Annotated[float, Field(..., title="Product Price", description="The price of the product SKU")]

    @classmethod
    @field_validator("price")
    def validate_price(cls, value):
        if value < 0:
            raise ValueError('Price must be greater than 0')
        return value


class Listing(BaseModel):
    """
    Product Listing, can contain multiple SKUs
    """

    id: str = Field(..., title="Product ID", description="The ID of the product listing")
    title: str = Field(..., title="Product Title", description="The title of the product listing")
    description: str = Field(..., title="Product Description", description="The description of the product listing")
    category: str = Field(..., title="Product Category", description="The category of the product listing")
    skus: list[SKU] = Field(..., title="Product SKUs", description="The SKUs of the product listing")
    views: int = Field(0, title="Product Views", description="The number of views of the product listing")
    rating: float = Field(0, title="Product Rating", description="The rating of the product listing")
    ownerUser: User = Field(..., title="Owner User", description="The owner of the product listing")

    @classmethod
    @field_validator("rating")
    def validate_rating(cls, value):
        if value < 0 or value > 5:
            raise ValueError('Rating must be between 0 and 5')
        return value

    @classmethod
    @field_validator("views")
    def validate_views(cls, value):
        if value <= 0:
            raise ValueError('Views must be greater than or equal to 0')
        return value

    @classmethod
    @field_validator("skus")
    def validate_skus(cls, value):
        if len(value) < 1:
            raise ValueError('At least one SKU is required')
        return value


class PrivilegedListing(Listing):
    """
    Contains private data, inherits from Listing. For sellers
    """
    sales: int = Field(0, title="Product Sales", description="The number of sales of the product listing")
    revenue: float = Field(0, title="Product Revenue", description="The revenue of the product listing")


class ListingGroup(ResponseSchema[List[Listing]]):
    """
    Response Model - Group of listings with metadata for pagination
    """
    pass
