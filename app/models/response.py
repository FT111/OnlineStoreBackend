from typing import TypeVar

from pydantic import BaseModel
from typing_extensions import Generic

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
