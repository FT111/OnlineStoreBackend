from pydantic import BaseModel, Field, EmailStr, model_validator, HttpUrl, field_validator
from typing import List, Optional, Union, Dict, Any, Tuple, Set
from typing_extensions import Annotated

from app.models.response import ResponseSchema


class UserCredentials(BaseModel):
    """
    User Credentials
    """

    email: EmailStr = Field(..., title="Email", description="The email of the user")
    password: str = Field(..., title="Password", description="The password of the user")


class Token(BaseModel):
    """
    Token schema
    """

    token: str = Field(..., title="Token", description="The token")
    expires: int = Field(..., title="Expires", description="The expiry of the token")


class Response:

    class TokenMeta(BaseModel):
        pass

    class Token(ResponseSchema[TokenMeta, Token]):
        """
        Category Response Model
        """
        pass

