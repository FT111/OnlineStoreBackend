from pydantic import BaseModel, Field, EmailStr, model_validator, HttpUrl, field_validator
from typing import List, Optional, Union, Dict, Any, Tuple, Set
from typing_extensions import Annotated


# Product SKU
class SKU(BaseModel):
    ID: str = Field(..., title="Product SKU", description="The SKU of the product")
    title: str = Field(..., title="Product Title", description="The title of the product SKU", max_length=50)
    description: str = Field(..., title="Product Description",
                             description="The short description of the product SKU", max_length=50)
    images: list[Union[str, None]] = Field(..., title="Product Images", description="The images of the product SKU")
    price: float = Annotated[float, Field(..., title="Product Price", description="The price of the product SKU")]

    @classmethod
    @field_validator("price")
    def validate_price(cls, value):
        if value < 0:
            raise ValueError('Price must be greater than 0')
        return value


# Product Listing, can contain multiple SKUs
class Listing(BaseModel):
    title: str = Field(..., title="Product Title", description="The title of the product listing")
    description: str = Field(..., title="Product Description", description="The description of the product listing")
    category: str = Field(..., title="Product Category", description="The category of the product listing")
    skus: list[SKU] = Field(..., title="Product SKUs", description="The SKUs of the product listing", min_length=1)
    views: int = Field(0, title="Product Views", description="The number of views of the product listing")
    ownerUserID: str = Field(..., title="Owner User", description="The owner of the product listing")


# Privileged Listing, inherits from Listing. For privileged users i.e Sellers
class PrivilegedListing(Listing):
    sales: int = Field(0, title="Product Sales", description="The number of sales of the product listing")
    revenue: float = Field(0, title="Product Revenue", description="The revenue of the product listing")
