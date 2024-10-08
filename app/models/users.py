
from pydantic import BaseModel, Field, EmailStr, model_validator, HttpUrl, field_validator
from typing import List, Optional, Union, Dict, Any, Tuple, Set
from typing_extensions import Annotated

import regex as re

from app.models.response import ResponseSchema


class User(BaseModel):
    """
    User Profile, for public viewing
    """

    id: str = Field(..., title="User ID", description="The ID of the user")
    username: str = Field(..., title="Username", description="The username of the user", max_length=50)
    profileURL: Union[str, None] = Field(None, title="Profile URL", description="The URL of the user's profile")
    profilePictureURL: Union[str, None] = Field(None, title="Profile Picture URL", description="The URL of the user's profile picture")
    bannerURL: Union[str, None] = Field(None, title="Banner URL", description="The URL of the user's banner")
    description: str = Field(..., title="Bio", description="The description of the user", max_length=100)
    joinedAt: int = Field(0, title="Joined At", description="The date the user joined")


class PrivilegedUser(User):
    """
    User's PII data, inherits from User.
    """

    firstName: str = Field(..., title="First Name", description="The first name of the user")
    surname: str = Field(..., title="Surname", description="The user's surname")
    email: EmailStr = Field(..., title="Email", description="The email of the user")
    streetAddress: Union[str, None] = Field(None, title="Street Address", description="The street address of the user")
    city: Union[str, None] = Field(None, title="City", description="The city of the user")
    province: Union[str, None] = Field(None, title="Region", description="The province of the user")
    country: Union[str, None] = Field(None, title="Country", description="The country of the user")
    listings: list[Union[str, None]] = Field(None, title="Listings", description="The listings of the user")

    @classmethod
    @field_validator("email")
    def validate_email(cls, value):
        if not re.match(r"[^@]+@[^@]+\.[^@]+", value):
            raise ValueError('Invalid email address')
        return value


class DatabaseUser(PrivilegedUser):
    """
    A complete user, for database storage
    """
    salt: str = Field(..., title="Salt", description="The salt of the user")
    hashedPassword: str = Field(..., title="Hashed Password", description="The hashed password of the user")


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
