from fastapi import APIRouter, Depends, HTTPException, Request, Form
from typing import List, Dict, Any

from pydantic import Field
from fastapi.security import OAuth2PasswordRequestForm
from starlette.responses import Response
from typing_extensions import Annotated, Union, Optional

from ..models.auth import Response as AuthResponse
from ..models.auth import UserCredentials, Token
from ..database.database import getDBSession
from ..functions import data
from ..functions.auth import authenticateUser, generateToken
from ..models.categories import Category, SubCategory
from ..models.categories import Response as CategoryResponse

import sqlite3

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post('/token', response_model=AuthResponse.Token)
async def authenticateCredentials(credentials: UserCredentials,
                                  conn: sqlite3.Connection = Depends(getDBSession)):
    """
    Get a token for the user
    :param credentials: The user's credentials. Contains email and password
    :param conn: SQL DB connection

    """

    # Authenticate the user using the given credentials
    user = authenticateUser(conn, credentials.email, credentials.password)
    # Return a 401 if the user is not correctly authenticated
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate a JWT token for the user
    token = generateToken(user['id'], user['emailAddress'])

    return AuthResponse.Token(meta={},
                              data=Token(token=token)
                              )

