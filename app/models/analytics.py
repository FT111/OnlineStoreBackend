from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, Field
from typing_extensions import Annotated, Union

from app.models.response import ResponseSchema


class Events:

	class Event(BaseModel, ABC):
		"""
		A base event model
		"""
		listingID: str = Field(description='The ID of the listing that the event is associated with',
							   examples=['ff6344c7-42f2-4746-a234-80e69b3266ff'])
		userID: Optional[str] = Field(description='The ID of the user that the event is associated with',
									  examples=['835b16c5-9440-4c44-9cc9-a9e70df9a882'])
		id: str = Field(description='The ID of the event',
						examples=['69249b6b-8fe6-49f2-848a-0d4dc7b273ed'])
		time: int = Field(description='The time at which the event was registered, as a unix timestamp',
						  examples=[1632931200])

		@abstractmethod
		def __str__(self):
			"""
			Return a string representation of the event
			This should be the name of the event type
			:return:
			"""
			pass

		@abstractmethod
		def __repr__(self):
			"""
			Return a string representation of the event
			This should be the data of the event
			:return:
			"""
			pass

	# @dataclass
	class ListingClick(Event):
		"""
		A model representing a listing click
		"""
		listingID: str = Field(description='The ID of the listing that was clicked',
							   examples=['ff6344c7-42f2-4746-a234-80e69b3266ff'])
		userID: Optional[str] = Field(description='The ID of the user that clicked the listing',
									  examples=['835b16c5-9440-4c44-9cc9-a9e70df9a882'])
		id: str = Field(description='The ID of the click event',
						examples=['69249b6b-8fe6-49f2-848a-0d4dc7b273ed'])
		time: int = Field(description='The time at which the click was registered, as a unix timestamp',
						  examples=[1632931200])

		def __str__(self):
			return 'click'

		def __repr__(self):
			return f'ListingClick({self.listingID}, {self.userID}, {self.id}, {self.time})'

	# @dataclass
	class ListingView(Event):
		"""
		A model representing a listing view
		"""
		listingID: str = Field(description='The ID of the listing that was viewed',
								examples=['ff6344c7-42f2-4746-a234-80e69b3266ff'])
		userID: Optional[str] = Field(description='The ID of the user that viewed the listing',
									   examples=['835b16c5-9440-4c44-9cc9-a9e70df9a882'])
		id: str = Field(description='The ID of the view event',
						 examples=['69249b6b-8fe6-49f2-848a-0d4dc7b273ed'])
		time: int = Field(description='The time at which the view was registered, as a unix timestamp',
						  examples=[1632931200])

		def __str__(self):
			return 'view'

		def __repr__(self):
			return f'ListingView({self.listingID}, {self.userID}, {self.id}, {self.time})'

	class ListingImpression(Event):
		"""
		A model representing a listing impression
		"""
		listingID: str = Field(description='The ID of the listing that was viewed',
								examples=['ff6344c7-42f2-4746-a234-80e69b3266ff'])
		userID: Optional[str] = Field(description='The ID of the user that engaged with the listing',
									   examples=['835b16c5-9440-4c44-9cc9-a9e70df9a882'])
		id: str = Field(description='The ID of the impression event',
						 examples=['69249b6b-8fe6-49f2-848a-0d4dc7b273ed'])
		time: int = Field(description='The time at which the impression was registered, as a unix timestamp',
						  examples=[1632931200])

		def __str__(self):
			return 'impression'

		def __repr__(self):
			return f'ListingImpression({self.listingID}, {self.userID}, {self.id}, {self.time})'


class Confirmation(BaseModel):
	"""
	Basic analytics confirmation model
	"""

	event: Union[Events.ListingClick, Events.ListingView] = Field(description='The action that was confirmed')


class Response:
	class ConfirmationMeta(BaseModel):
		"""
		Metadata for a confirmation response
		"""
		registered: bool = Annotated[bool, Field(description='Whether the analytics action was registered', examples=[True])]

	class ConfirmationResponse(ResponseSchema[ConfirmationMeta, Confirmation]):
		"""
		A response containing a confirmation
		"""
		pass
