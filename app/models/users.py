import time
from dataclasses import dataclass

from pydantic import BaseModel, Field, EmailStr, model_validator, HttpUrl, field_validator
from typing import List, Optional, Union, Dict, Any, Tuple, Set
from typing_extensions import Annotated

import regex as re

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
    profilePictureURL: Union[str, None] = Field(None, title="Profile Picture URL", description="The URL of the user's profile picture")
    bannerURL: Union[str, None] = Field(None, title="Banner URL", description="The URL of the user's banner")
    description: Union[str, None] = Field(None, title="Bio", description="The description of the user", max_length=100)
    joinedAt: int = Field(time.time(), title="Joined At", description="The date the user joined")


class UserDetail(User):
    """
    User's content, inherits from User.
    """
    listingIDs: Union[list, None] = Field(None, title="Listings", description="The listings of the user")


class PrivilegedUser(UserDetail):
    """
    User's PII data, inherits from UserDetail.
    """

    firstName: str = Field(..., title="First Name", description="The first name of the user")
    surname: str = Field(..., title="Surname", description="The user's surname")
    email: EmailStr = Field(..., title="Email", description="The email of the user")
    streetAddress: Union[str, None] = Field(None, title="Street Address", description="The street address of the user")
    city: Union[str, None] = Field(None, title="City", description="The city of the user")
    province: Union[str, None] = Field(None, title="Region", description="The province of the user")
    country: Union[str, None] = Field(None, title="Country", description="The country of the user")

    @classmethod
    @field_validator("email")
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


class UserSubmission(PrivilegedUser):
    """
    User Submission Model
    """
    password: str = Field(..., title="Plaintext Input Password")


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
