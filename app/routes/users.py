from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any
from typing_extensions import Annotated, Union, Optional

from ..database.database import getDBSession
from ..functions import data
from ..functions.auth import userRequired
from ..models.users import User, PrivilegedUser, UserSubmission
from ..models.users import Response as UserResponse
from ..models.listings import Response as ListingResponses

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
	"""
	Create a new user in the database.
	:param user: The user to create stored in a Pydantic model
	:param conn: SQL DB connection
	:return: The user created
	"""

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


@router.get('/{userID}/listings', response_model=ListingResponses.Listings)
async def getUserListings(
		userID: str,
		conn: sqlite3.Connection = Depends(getDBSession)):
	"""
	Get all listings by a user.
	:param userID: A user's id
	:param conn: SQL DB connection
	:return: 404 or the user's listings
	"""

	# Queries the database for the user's listings
	listings = data.getListingsByUserID(conn, userID)
	# Return a 404 if the user is not found
	if not listings:
		raise HTTPException(status_code=404, detail="User not found")

	topListingCategories = defaultdict(int)
	for listing in listings:
		topListingCategories[listing.category] += 1

	# Return the user's listings in standard format
	return ListingResponses.Listings(meta={
		'total': len(listings),
		'topCategories': sorted(dict(topListingCategories))
	}, data=listings)
