from typing import List, Optional, Union, Dict

from pydantic import BaseModel, Field, field_validator
from typing_extensions import Annotated

from app.models.response import ResponseSchema
from app.models.users import User


class SKU(BaseModel):
    """
    Product SKU/Variant
    """
    id: str = Field(..., title="Product SKU", description="The SKU of the product")
    title: str = Field(..., title="Product Title", description="The title of the product SKU", max_length=50)
    images: List[str] = Field([], title="Product Images", description="The images of the product SKU")
    price: int = Annotated[int, Field(..., title="Product Price", description="The price of the product SKU")]
    discount: Optional[int] = Field(None, title="Product Discount", description="The discount of the product SKU")

    options: Optional[Dict[str, str]] = Field({}, title="SKU Option Values",
                                              description="The values of the SKU's assigned options, "
                                                          "paired with the option type",
                                              )

    @classmethod
    @field_validator("price")
    def validate_price(cls, value):
        if value <= 0:
            raise ValueError('Price must be greater than 0')
        return value

    @classmethod
    @field_validator("discount")
    def validate_discount(cls, value):
        if value is not None and (value < 0 or value > 99):
            raise ValueError('Discount must be between 0 and 99')
        return value

    # def __init__(self, *args, **data):
    #     super().__init__()
    #
        # # Sanitise image names
        # print(self.images)
        # if len(self.images) != 0:
        #     for count, image in enumerate(self.images):
        #         imgName = str(image).strip().replace(" ", "_")
        #         imgName = re.sub(r"(?u)[^-\w.]", "", imgName)
        #         if imgName in {"", ".", "..", "CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7"}:
        #             raise NameError("Invalid image name")
        #         self.images[count] = imgName


class SKUWithStock(SKU):
    """
    Contains stock, inherits from SKU. For sellers
    """
    stock: int = Field(..., title="Product Stock", description="The stock of the product SKU")

    @field_validator("stock")
    def validate_stock(cls, value):
        if value < 0:
            raise ValueError('Stock must be greater than or equal to 0')
        return value


class SKUSubmission(BaseModel):
    """
    SKU Submission Model
    """
    title: str = Field(..., title="Product Title", description="The title of the product SKU", max_length=50)
    images: List[Optional[str]] = Field([], title="Product Images", description="The images of the product SKU")
    price: int = Annotated[int, Field(..., title="Product Price",
                                      description="The price of the product SKU. Stored as an integer *100")]
    discount: Optional[int] = Field(None, title="Product Discount", description="The discount of the product SKU")
    stock: int = Field(..., title="Product Stock", description="The stock of the product SKU")

    @field_validator("title")
    def validate_title(cls, value):
        if len(value) < 1 or len(value) > 30:
            raise ValueError('Title must be between 1 and 30 characters')
        return value

    @field_validator("price")
    def validate_price(cls, value):
        if int(value) <= 0:
            raise ValueError('Price must be greater than 0')
        return value

    @field_validator("discount")
    def validate_discount(cls, value):
        if value is not None and (value < 0 or value > 99):
            raise ValueError('Discount must be between 0 and 99')
        return value

    @field_validator("stock")
    def validate_stock(cls, value):
        if value < 0:
            raise ValueError('Stock must be greater than or equal to 0')
        return value


class Listing(BaseModel):
    """
    Product Listing, can contain multiple SKUs
    """

    id: Union[str, int] = Field(..., title="Product ID", description="The ID of the product listing")
    title: str = Field(..., title="Product Title", description="The title of the product listing")
    description: str = Field(..., title="Product Description", description="The description of the product listing")
    images: List[Optional[str]] = Field([], title="Product Images",
                                        description="The images of the product listing. List of URLs")
    condition: str = Field('New', title="Product Condition", description="The condition of the product listing")

    subCategory: str = Field(None, title="Product Subcategory", description="The subcategory of the product listing")
    category: str = Field(..., title="Product Category", description="The category of the product listing")
    basePrice: Union[str, float, None] = Field('0', title="Product Base Price",
                                               description="The base price of the product listing")

    hasDiscount: bool = Field(False, title="Has Discount", description="Whether the product listing has a discount")
    multipleSKUs: bool = Field(False, title="Multiple SKUs", description="Whether the product listing has multiple SKUs")
    views: int = Field(0, title="Product Views", description="The number of views of the product listing")
    rating: float = Field(0, title="Product Rating", description="The rating of the product listing")
    addedAt: Optional[int] = Field(..., title="Added At", description="The datetime the product listing was added")
    ownerUser: Optional[Union[User, Dict]] = Field(..., title="Owner User",
                                                   description="The owner of the product listing")
    public: bool = Field(True, title="Public", description="Whether the product listing is public")

    @field_validator("rating")
    def validate_rating(cls, value):
        assert 0 <= value <= 5, 'Rating must be between 0 and 5'
        return value

    @field_validator("views")
    def validate_views(cls, value):
        if value < 0:
            raise ValueError('Views must be greater than or equal to 0')
        return value

    @field_validator("title")
    def validate_title(cls, value):
        if len(value) < 1 or len(value) > 40:
            raise ValueError('Title must be between 1 and 40 characters')
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
    skuOptions: Dict[str, List[str]] = Field({}, title="SKU Options",
                                              description="The options for a listing's SKU, paired with the option type")


class ListingWithSales(ListingWithSKUs):
    """
    Contains private data, inherits from Listing. For sellers
    Also used to show statistics on a listing
    """
    skus: Optional[List[SKUWithStock]] = Field(..., title="Product SKUs",
                                               description="The SKUs of the product listing")
    clicks: int = Field(0, title="Product Clicks", description="The number of clicks on the product listing")

    # sales: int = Field(0, title="Product Sales", description="The number of sales of the product listing")
    # revenue: float = Field(0, title="Product Revenue", description="The revenue of the product listing")


class ListingSubmission(BaseModel):
    """
    Base Listing for creating a new listing.
    Contains the minimum data required for a listing.
    """
    title: str = Field(..., title="Product Title", description="The title of the product listing")
    description: str = Field('', title="Product Description", description="The description of the product listing")
    subCategory: str = Field(..., title="Product Subcategory", description="The subcategory of the product listing")
    category: str = Field(..., title="Product Category", description="The category of the product listing")
    public: bool = Field(False, title="Public", description="Whether the product listing is public")

    @field_validator("title")
    def validate_title(cls, value):
        if len(value) < 1 or len(value) > 40:
            raise ValueError('Title must be between 1 and 40 characters')
        return value

    @field_validator("description")
    def validate_description(cls, value):
        if len(value) > 100:
            raise ValueError('Description must be less than 200 characters')
        return value


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
        topCategories: Optional[List] = Field(None, title="Top Categories",
                                              description="The top categories for the listings")

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

    class SKU(ResponseSchema[ListingMeta, SKU]):
        """
        Response Model - Single SKU
        """
        pass
