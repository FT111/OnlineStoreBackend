import time
import uuid
from dataclasses import dataclass
from typing import Optional, Union

import regex as re
from pydantic import BaseModel, Field, EmailStr, field_validator

from app.models.response import ResponseSchema


@dataclass
class JWTUser:
	"""
	Model used to store JWT and user data in a JWT
	"""
	id: str
	email: str
	expiry: int


class User(BaseModel):
	"""
	User Profile, for public viewing
	"""

	id: Optional[str] = Field(None, title="User ID", description="The ID of the user")
	username: str = Field(..., title="Username", description="The username of the user", max_length=50)
	profileURL: Union[str, None] = Field(None, title="Profile URL", description="The URL of the user's profile")
	profilePictureURL: Union[str, None] = Field(None, title="Profile Picture URL",
												description="The URL of the user's profile picture")
	rating: float = Field(0.0, title="Rating", description="The rating of the user")
	bannerURL: Union[str, None] = Field(None, title="Banner URL", description="The URL of the user's banner")
	description: Union[str, None] = Field(None, title="Bio", description="The description of the user", max_length=100)
	joinedAt: int = Field(int(time.time()), title="Joined At", description="The date the user joined")


class UserDetail(User):
	"""
	User's content, inherits from User.
	"""
	listingIDs: Union[list, None] = Field(None, title="Listings", description="The listings of the user")
	sales: int = Field(0, title="Sales", description="The sales of the user")


class PrivilegedUser(UserDetail):
	"""
	User's PII data, inherits from UserDetail.
	"""

	firstName: str = Field(..., title="First Name", description="The first name of the user")
	surname: str = Field(..., title="Surname", description="The user's surname")
	emailAddress: EmailStr = Field(..., title="Email", description="The email of the user")
	balance: int = Field(0, title="Balance", description="The balance of the user. Formatted in pence")
	allTimeBalance: int = Field(0, title="All Time Balance",
								description="The balance of the user before withdrawals. Formatted in pence. Still includes refunds.")
	streetAddress: Union[str, None] = Field(None, title="Street Address", description="The street address of the user")
	addressLine1: Union[str, None] = Field(None, title="Address Line 1", description="The first line of the address")
	addressLine2: Union[str, None] = Field(None, title="Address Line 2",
										   description="The second line of the address, optional")
	city: Union[str, None] = Field(None, title="City", description="The city of the user")
	country: Union[str, None] = Field(None, title="Country", description="The country of the user")
	postcode: Union[str, None] = Field(None, title="Postcode", description="The postcode of the user")

	@classmethod
	@field_validator("emailAddress")
	def validate_email(cls, value):
		if not re.match(r"[^@]+@[^@]+\.[^@]+", value):
			raise ValueError('Invalid email address')
		if not len(value) > 0:
			raise ValueError('Email must not be empty')
		if not len(value) <= 320:
			raise ValueError('Email must be less than or equal to 320 characters')
		return value

	@classmethod
	@field_validator("firstName")
	def validate_firstName(cls, value):
		if not len(value) > 0:
			raise ValueError('Name must not be empty')
		return value

	@field_validator("surname")
	def validate_surname(cls, value):
		if not len(value) > 0:
			raise ValueError('Surname must not be empty')
		return value


class PwdResetRequestSubmission(BaseModel):
	"""
	Password Reset Request Submission Model
	"""
	email: EmailStr = Field(..., title="Email", description="The email of the user")


class PwdResetSubmission(BaseModel):
	"""
	Password Reset Submission Model
	"""
	password: str = Field(..., title="Password", description="The new password, as plaintext")
	token: str = Field(..., title="Token", description="The token for the password reset request")


@dataclass
class PwdResetRequest:
	"""
	Password Reset Request Model
	"""
	hashedId: str = Field(None, title="Hashed ID",
						  description="The ID of the password reset request, hashed in the database")
	id: str = Field(uuid.uuid4(), title="ID", description="The ID of the password reset request")
	addedAt: int = Field(time.time(), title="Added At", description="The date the request was added")
	user: PrivilegedUser = Field(..., title="User", description="The user requesting the password reset")


class UserSubmission(PrivilegedUser):
	"""
	User Submission Model
	"""
	password: str = Field(..., title="Plaintext Input Password")


class UserReviewSubmission(BaseModel):
	"""
	User Review Submission Model
	"""
	# reviewerID: str = Field(..., title="Reviewer ID", description="The ID of the reviewer")
	# reviewedID: str = Field(..., title="Reviewed User", description="The ID of the user being reviewed")
	rating: int = Field(..., title="Rating", description="The rating given by the reviewer")
	description: Union[str, None] = Field(None, title="Comment", description="The comment given by the reviewer")


class UserReview(BaseModel):
	"""
	User Review Model
	"""
	id: str = Field(..., title="ID", description="The ID of the review")
	reviewer: User = Field(..., title="Reviewer ID", description="The ID of the reviewer")
	# reviewed: User = Field(..., title="Reviewed User", description="The user being reviewed")
	rating: int = Field(..., title="Rating", description="The rating given by the reviewer")
	description: Union[str, None] = Field(None, title="Comment", description="The comment given by the reviewer")
	addedAt: int = Field(..., title="Added At", description="The date, as a unix epoch integer, the review was added")


class Response:
	class UserMeta(BaseModel):
		pass

	class User(ResponseSchema[UserMeta, User]):
		"""
		User Response Model
		"""
		pass

	class PrivilegedUserMeta(BaseModel):
		pass

	class PrivilegedUser(ResponseSchema[PrivilegedUserMeta, PrivilegedUser]):
		"""
		Privileged User Response Model
		"""
		pass

	class UserReview(ResponseSchema[UserMeta, UserReview]):
		pass
