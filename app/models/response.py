
from pydantic import BaseModel, Field, EmailStr, model_validator, HttpUrl, field_validator
from typing import List, Optional, Union, Dict, Any, Tuple, Set, TypeVar
from typing_extensions import Annotated, Generic

data = TypeVar("data")


class ResponseSchema(BaseModel, Generic[data]):
    meta: Dict[str, Any] = Field(..., title="Metadata", description="The metadata of the response")
    data: data
    