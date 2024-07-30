
from pydantic import BaseModel, Field, EmailStr, model_validator, HttpUrl, field_validator
from typing import List, Optional, Union, Dict, Any, Tuple, Set, TypeVar
from typing_extensions import Annotated, Generic

meta = TypeVar("meta")
data = TypeVar("data")


class ResponseSchema(BaseModel, Generic[meta, data]):
    meta: meta
    data: data
    