from pydantic import BaseModel, Field, EmailStr, model_validator, HttpUrl, field_validator
from typing import List, Optional, Union, Dict, Any, Tuple, Set
from typing_extensions import Annotated

from app.models.users import User, PrivilegedUser, DatabaseUser
from app.models.response import ResponseSchema


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

    subCategories: Optional[List[SubCategory]] = Field(None, title="Subcategories", description="The subcategories of the category")

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

    class Categories(ResponseSchema[CategoriesMeta, List[Category]]):
        """
        Response Model for multiple categories
        """
        pass
