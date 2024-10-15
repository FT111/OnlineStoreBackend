from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any
from typing_extensions import Annotated, Union, Optional

from ..database.database import getDBSession
from ..functions import data
from ..functions.auth import userRequired
from ..models.users import User, PrivilegedUser, UserSubmission
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
		user: UserSubmission,
		conn: sqlite3.Connection = Depends(getDBSession)):

	user = data.createUser(conn, user)

	return UserResponse.User(meta={}, data=user)


@router.get('/{userID}', response_model=UserResponse.User)
async def getUser(
		userID: str,
		conn: sqlite3.Connection = Depends(getDBSession)):
	"""
	Get a user by their ID
	:param userID: A user's id
	:param conn: SQL DB connection
	:return: 404 or the user
	"""

	# Queries the database for the user
	user = data.getUserByID(conn, userID)
	# Return a 404 if the user is not found
	if not user:
		raise HTTPException(status_code=404, detail="User not found")

	# Return the user in standard format
	return UserResponse.User(meta={}, data=user)

