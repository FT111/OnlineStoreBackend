from pydantic import BaseModel, Field, EmailStr

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


class Response:
	class TokenMeta(BaseModel):
		pass

	class Token(ResponseSchema[TokenMeta, Token]):
		"""
		Category Response Model
		"""
		pass
