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
    title: str = Field(..., title="Product TitleŸ", description="The title of the product SKU", max_length=50)
    description: str = Field(..., title="Product Description",
                             description="The short description of the product SKU", max_length=50)
    condition: str = Field(..., title="Product Condition", description="The condition of the product SKU")
    images: Optional[List[str]] = Field(..., title="Product Images", description="The images of the product SKU")
    price: float = Annotated[float, Field(..., title="Product Price", description="The price of the product SKU")]

    @classmethod
    @field_validator("price")
    def validate_price(cls, value):
        if value < 0:
            raise ValueError('Price must be greater than 0')
        return value


class SKUWithStock(SKU):
    """
    Contains stock, inherits from SKU. For sellers
    """
    stock: int = Field(..., title="Product Stock", description="The stock of the product SKU")

    @classmethod
    @field_validator("stock")
    def validate_stock(cls, value):
        if value < 0:
            raise ValueError('Stock must be greater than or equal to 0')
        return value


class Listing(BaseModel):
    """
    Product Listing, can contain multiple SKUs
    """

    id: Optional[int] = Field(..., title="Product ID", description="The ID of the product listing")
    title: str = Field(..., title="Product Title", description="The title of the product listing")
    description: str = Field(..., title="Product Description", description="The description of the product listing")
    subCategory: str = Field(None, title="Product Subcategory", description="The subcategory of the product listing")
    category: str = Field(..., title="Product Category", description="The category of the product listing")
    basePrice: Optional[int] = Field(0, title="Product Base Price", description="The base price of the product listing")
    hasDiscount: bool = Field(False, title="Has Discount", description="Whether the product listing has a discount")
    multipleSKUs: bool = Field(False, title="Multiple SKUs", description="Whether the product listing has multiple SKUs")
    views: int = Field(0, title="Product Views", description="The number of views of the product listing")
    rating: float = Field(0, title="Product Rating", description="The rating of the product listing")
    addedAt: Optional[int] = Field(..., title="Added At", description="The datetime the product listing was added")
    ownerUser: Optional[User] = Field(..., title="Owner User", description="The owner of the product listing")

    @field_validator("rating")
    def validate_rating(cls, value):
        assert 0 <= value <= 5, 'Rating must be between 0 and 5'
        return value

    @field_validator("views")
    def validate_views(cls, value):
        if value < 0:
            raise ValueError('Views must be greater than or equal to 0')
        return value

    # @classmethod
    # @field_validator("skus")
    # def validate_skus(cls, value):
    #     if len(value) < 1:
    #         raise ValueError('At least one SKU is required')
    #     return value


class ListingWithSKUs(Listing):
    """
    Contains SKUs, inherits from Listing. Used for detail on a specific listing
    """
    skus: List[SKU] = Field(..., title="Product SKUs", description="The SKUs of the product listing")


class ListingWithSales(Listing):
    """
    Contains private data, inherits from Listing. For sellers
    """
    skus: List[SKUWithStock] = Field(..., title="Product SKUs", description="The SKUs of the product listing")
    sales: int = Field(0, title="Product Sales", description="The number of sales of the product listing")
    revenue: float = Field(0, title="Product Revenue", description="The revenue of the product listing")


class Response:
    """
    REST API Response Models for Listings
    """

    class ListingsMeta(BaseModel):
        """
        Metadata for a listings group response
        """
        total: int = Field(0, title="Total Listings", description="The total number of listings returned")
        limit: int = Field(10, title="Limit", description="The limit of listings per page")
        offset: int = Field(0, title="Offset", description="The offset of listings")
        query: Union[str, None] = Field(None, title="Query", description="The query used for the listings")
        category: Union[str, None] = Field(None, title="Category", description="The category for the listings")
        sort: Optional[str] = Field('relevance', title="Sort", description="The sort used for the listings")
        order: Optional[str] = Field('desc', title="Order", description="The order used for the listings")

    class ListingMeta(BaseModel):
        pass

    # Specifies the types of the response model
    class Listings(ResponseSchema[ListingsMeta,
                   List[Union[Listing, ListingWithSales]]]):
        """
        Response Model - Group of listings with metadata for pagination
        """
        pass

    class Listing(ResponseSchema[ListingMeta,
                  Union[ListingWithSKUs, ListingWithSales]]):
        """
        Response Model - Single listing
        """
        pass
