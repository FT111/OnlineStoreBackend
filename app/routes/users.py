from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any
from typing_extensions import Annotated, Union, Optional

from ..database.database import getDBSession
from ..functions import data
from ..functions.auth import userRequired
from ..models.users import User, PrivilegedUser
from ..models.users import Response as UserResponse

import cachetools.func
import sqlite3

router = APIRouter(prefix="/users", tags=["users"])


@router.get('/me', response_model=UserResponse.User)
async def getMe(
		conn: sqlite3.Connection = Depends(getDBSession),
		user: Dict = Depends(userRequired)):
	"""
	Get the current user
	"""

	userDetails = data.getUserByID(conn, user['id'])

	return UserResponse.User(meta={}, data=userDetails)


@router.put('/', response_model=UserResponse.User)
async def newUser(
		user: User,
		conn: sqlite3.Connection = Depends(getDBSession)):


	return UserResponse.User(meta={},
							 data=user)



