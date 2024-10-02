from fastapi import APIRouter, Depends, HTTPException, Request
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
async def authenticateCredentials(response: Response,
                                  credentials: OAuth2PasswordRequestForm = Depends(),
                                  conn: sqlite3.Connection = Depends(getDBSession)):
    """
    Get a token for the user
    """

    # Authenticate the user using the given credentials
    user = authenticateUser(conn, credentials.username, credentials.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate a JWT token for the user and sets it as a cookie for later use
    token = generateToken(user['id'], user['emailAddress'])

    response.set_cookie(key="token", value=token, httponly=True)
    return AuthResponse.Token(meta={},
                              data=Token(token=token)
                              )
