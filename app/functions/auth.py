import time
from sqlite3 import Connection

import bcrypt
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, exceptions as joseExceptions
from starlette.requests import Request
from typing_extensions import Union

from . import data as data
from ..database.database import getDBSession
from ..database.databaseQueries import Queries
from ..models.listings import ListingWithSKUs

JWT_EXPIRY = 604_800
# SECRET_KEY = secrets.token_urlsafe(32)
SECRET_KEY = 'this_will_be_replaced_by_a_secret_key'

# bcryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto")
Oauth2Bearer = OAuth2PasswordBearer(tokenUrl="auth/token")


def generateToken(userID, userEmail):
    """
    Generates a signed JWT token containing the user's ID and email
    """

    expiry = time.time() + JWT_EXPIRY

    return jwt.encode({'id': userID, 'email': userEmail, 'exp': expiry}, SECRET_KEY, algorithm='HS256')


def validateToken(token: str) -> Union[dict, bool]:
    """
    Validates a signed JWT token
    """

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except joseExceptions.JWTError:
        return False


def authenticateUser(dbSession: Connection, email: str, password: str):
    """
    Authenticates a user by email and password
    Fetches the user's hash and salt from the database
    """

    time.sleep(1)

    # Gets the user's data
    user = Queries.Users.getUserByEmail(dbSession, email)

    # Fails if no user is found
    if not user:
        return False

    hashedPassword = str(user['passwordHash'])

    # Validates given credentials. Uses bcrypt checkpw to avoid timing attacks
    if bcrypt.checkpw(password.encode('utf-8'), hashedPassword.encode('utf-8')):
        # Returns the user's data if the password is correct
        return user
    else:
        return False


def generateSalt() -> str:
    """
    Generates a salt for hashing passwords
    """

    return bcrypt.gensalt().decode('utf-8')


def userRequired(request: Request) -> dict:
    """
    Dependency for requiring a valid user

    Returned user is trusted, verified by a signed token.
    """

    if not request.state.user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return request.state.user


def userOptional(request: Request) -> Union[dict, None]:
    """
    Dependency for using user information if available
    """

    if not request.state.user:
        return None

    return request.state.user


def hashPassword(password, salt):
    return bcrypt.hashpw(password.encode('utf-8'), salt.encode('utf-8'))


def verifyListingOwnership(listingID, user) -> ListingWithSKUs:
    # Fetches parent listing
    listing = data.getListingByID(getDBSession(),
                                  listingID,
                                  includePrivileged=True,
                                  user=user)
    # Checks if the listing exists
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    # Checks if the requester is the owner of the listing
    if user['id'] != listing.ownerUser.id:
        raise HTTPException(status_code=403, detail="You do not have permission to edit this listing")

    return listing
