from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any

from pydantic import Field
from typing_extensions import Annotated, Union, Optional

from ..models.auth import Response as AuthResponse
from ..models.auth import UserCredentials, Token
from ..database.database import getDBSession
from ..functions import data
from ..functions.auth import authenticateUser
from ..models.categories import Category, SubCategory
from ..models.categories import Response as CategoryResponse

import sqlite3

router = APIRouter(prefix="/auth", tags=["categories"])


@router.post('/token', response_model=AuthResponse.Token)
async def authenticateToken(credentials: UserCredentials,
                            conn: sqlite3.Connection = Depends(getDBSession)):
    """
    Get a token for the user
    """

    auth = authenticateUser(conn, credentials.email, credentials.password)
    return AuthResponse.Token(meta={},
                              data=Token(token='983q9812348923yriwyuegf', expires=2293429348023)
                              )
