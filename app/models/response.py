
from pydantic import BaseModel, Field, EmailStr, model_validator, HttpUrl, field_validator
from typing import List, Optional, Union, Dict, Any, Tuple, Set, TypeVar
from typing_extensions import Annotated, Generic

T = TypeVar("T")


class ResponseSchema(BaseModel, Generic[T]):
    meta: Dict[str, Any] = Field(..., title="Meta", description="The metadata of the response")
    data: Union[List[Dict[str, Any]], Dict[str, Any]] = Field(..., title="Data", description="The data of the response")
    