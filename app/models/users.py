
from pydantic import BaseModel, Field, EmailStr, model_validator, HttpUrl, field_validator
from typing import List, Optional, Union, Dict, Any, Tuple, Set
from typing_extensions import Annotated


# Public User Profile
class User(BaseModel):
    username: str = Field(..., title="Username", description="The username of the user", max_length=50)
    profilePictureURL: HttpUrl = Field(..., title="Profile Picture URL", description="The URL of the user's profile picture")
    description: str = Field(..., title="Bio", description="The description of the user", max_length=100)


# User Profile containing PII, for processing and the user themselves
class PrivilegedUser(User):
    email: EmailStr = Field(..., title="Email", description="The email of the user")
    password: str = Field(..., title="Password", description="The password of the user", min_length=8)
    phone: str = Field(..., title="Phone", description="The phone number of the user", max_length=15)
    address: str = Field(..., title="Address", description="The address of the user", max_length=100)
    listings: list[Union[str, None]] = Field(..., title="Listings", description="The listings of the user")
    sales: int = Field(0, title="Sales", description="The number of sales of the user")
