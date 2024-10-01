import bcrypt
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt
import time
import secrets
from sqlite3 import Connection
from ..database.databaseQueries import Queries

JWT_EXPIRY = 604_800
SECRET_KEY = secrets.token_urlsafe(32)

bcryptContext = CryptContext(schemes=["bcrypt"], deprecated="auto")
Oauth2Bearer = OAuth2PasswordBearer(tokenUrl="auth/token")


def generateToken(username, password):
    """
    Generates a token
    """

    expiry = time.time() + JWT_EXPIRY

    return jwt.encode({'username': username, 'password': password, 'exp': expiry}, SECRET_KEY, algorithm='HS256')


def authenticateUser(dbSession: Connection, email: str, password: str):
    """
    Authenticates a user by email and password
    """

    user = Queries.Users.getUserByEmail(dbSession, email)

    # Fails if no user is found
    if not user:
        return False

    hashedPassword = user['passwordHash']
    salt = user['passwordSalt']
    password += salt

    # Uses bcrypt to avoid timing attacks
    if bcrypt.checkpw(password.encode('utf-8'), hashedPassword.encode('utf-8')):
        return True
    else:
        return False


