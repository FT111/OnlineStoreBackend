
from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any

from pydantic import Field
from typing_extensions import Annotated, Union, Optional

from ..models.auth import Response as AuthResponse
from ..models.auth import UserCredentials
from ..database.database import getDBSession
from ..functions import data
from ..functions.auth import authenticateUser
from ..models.categories import Category, SubCategory
from ..models.categories import Response as CategoryResponse

import sqlite3

router = APIRouter(prefix="/auth", tags=["categories"])


@router.post('/token', response_model=AuthResponse)
async def authenticateToken(credentials: UserCredentials,
                            conn: sqlite3.Connection = Depends(getDBSession)):

    """
    Get a token for the user
    """

    return authenticateUser(conn, credentials.email, credentials.password)



