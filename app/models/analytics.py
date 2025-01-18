from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from app.models.response import ResponseSchema


class Events:

	@dataclass
	class Event(ABC):
		"""
		A base event model
		"""
		pass

	@dataclass
	class ListingClick(Event):
		"""
		A model representing a listing click
		"""
		listingID: UUID = Field(description='The ID of the listing that was clicked', examples=['ff6344c7-42f2-4746-a234-80e69b3266ff'])
		userID: Optional[UUID] = Field(description='The ID of the user that clicked the listing', examples=['835b16c5-9440-4c44-9cc9-a9e70df9a882'])
		id: UUID = Field(description='The ID of the click event', examples=['69249b6b-8fe6-49f2-848a-0d4dc7b273ed'])
		time: int = Field(description='The time at which the click was registered, as a unix timestamp', examples=[1632931200])

		def __repr__(self):
			return f'ListingClick({self.listingID}, {self.userID}, {self.id}, {self.time})'

	@dataclass
	class ListingView(Event):
		"""
		A model representing a listing view
		"""
		listingID: UUID = Field(description='The ID of the listing that was viewed', examples=['ff6344c7-42f2-4746-a234-80e69b3266ff'])
		userID: Optional[UUID] = Field(description='The ID of the user that viewed the listing', examples=['835b16c5-9440-4c44-9cc9-a9e70df9a882'])
		id: UUID = Field(description='The ID of the view event', examples=['69249b6b-8fe6-49f2-848a-0d4dc7b273ed'])
		time: int = Field(description='The time at which the view was registered, as a unix timestamp', examples=[1632931200])

		def __repr__(self):
			return f'ListingView({self.listingID}, {self.userID}, {self.id}, {self.time})'


class Event(Enum):
	"""
	An enum representing different types of analytics events
	"""
	click = Events.ListingClick
	view = Events.ListingView


class Confirmation(BaseModel):
	"""
	Basic analytics confirmation model
	"""

	registered: bool = Annotated[bool, Field(description='Whether the analytics action was registered', examples=[True])]


class Response:
	class ConfirmationMeta(BaseModel):
		"""
		Metadata for a confirmation response
		"""
		action: Event = Field(description='The action that was confirmed', examples=[Event.click])

	class ConfirmationResponse(ResponseSchema[ConfirmationMeta, Confirmation]):
		"""
		A response containing a confirmation
		"""
		pass
