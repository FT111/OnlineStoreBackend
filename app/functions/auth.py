import bcrypt
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt, exceptions as joseExceptions
import time
import secrets
from sqlite3 import Connection

from starlette.requests import Request
from typing_extensions import Union

from ..database.databaseQueries import Queries


JWT_EXPIRY = 604_800
SECRET_KEY = secrets.token_urlsafe(32)

bcryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto")
Oauth2Bearer = OAuth2PasswordBearer(tokenUrl="auth/token")


def generateToken(userID, userEmail):
    """
    Generates a signed JWT token containing the user's ID and email
    """

    expiry = time.time() + JWT_EXPIRY

    return jwt.encode({'id': userID, 'email': userEmail, 'exp': expiry}, SECRET_KEY, algorithm='HS256')


def authenticateUser(dbSession: Connection, email: str, password: str):
    """
    Authenticates a user by email and password
    """

    # Gets the user's data
    user = Queries.Users.getUserByEmail(dbSession, email)

    # Fails if no user is found
    if not user:
        return False

    # Appends the salt to the given password
    hashedPassword = user['passwordHash']
    salt = user['passwordSalt']
    password += salt

    # Validates given credentials. Uses bcrypt to avoid timing attacks
    if bcrypt.checkpw(password.encode('utf-8'), hashedPassword.encode('utf-8')):
        # Returns the user's data if the password is correct
        return user
    else:
        return False


def checkToken(token: str) -> Union[dict, bool]:
    """
    Validates a signed JWT token
    """

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except joseExceptions.JWTError:
        return False


def userRequired(request: Request) -> Union[dict, bool]:
    """
    Dependency for checking if a user is logged-in
    User data is gathered via JWT token in middleware
    """

    if not request.state.user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return request.state.user


def userOptional(request: Request) -> Union[dict, bool]:
    """
    Dependency for using user information if available
    """

    if not request.state.user:
        return False

    return request.state.user
