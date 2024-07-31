
from pydantic import BaseModel, Field, EmailStr, model_validator, HttpUrl, field_validator
from typing import List, Optional, Union, Dict, Any, Tuple, Set, TypeVar
from typing_extensions import Annotated, Generic

meta = TypeVar("meta")
data = TypeVar("data")


class ResponseSchema(BaseModel, Generic[meta, data]):
    """
    Standard Response Schema for all API responses

    Not directly used in responses, but used as a template for individual response models

    Attributes:
    meta: Information regarding the response itself
    data: The data returned by the API
    """
    meta: meta
    data: data
    