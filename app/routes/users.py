import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import StreamingResponse

from ..database import database
from ..functions.auth import userRequired, userOptional, generateToken
from ..functions.data import DataRepository
from ..models.auth import Response as AuthResponse, Token
from ..models.listings import Response as ListingResponses
from ..models.users import Response as UserResponse
from ..models.users import UserSubmission

router = APIRouter(prefix="/users", tags=["users"])


@router.get('/me', response_model=UserResponse.User)
async def getMe(user: Dict = Depends(userRequired),
				):
	"""
	Get the current user
	"""

	data = DataRepository(database.db)

	userDetails = data.getUserByID(user['id'])

	return UserResponse.User(meta={}, data=userDetails)


@router.put('/', response_model=AuthResponse.Token)
async def newUser(
		user: UserSubmission,
		):
	"""
	Create a new user in the database.
	:param conn: SQL DB connection
	:param user: The user to create stored in a Pydantic model
	:return: The user created
	"""

	data = DataRepository(database.db)

	user = data.createUser(user)
	token = generateToken(user.id, user.email)

	return AuthResponse.Token(meta={}, data=Token(token=token))


@router.get('/{userID}', response_model=UserResponse.User)
async def getUser(
		userID: str,
		includePrivileged: bool = False,
		user: Dict = Depends(userOptional),
		):
	"""
	Get a user by their ID
	:param user:
	:param includePrivileged: Whether to include private information
	:param userID: A user's id
	:param conn: SQL DB connection
	:return: 404 or the user
	"""

	data = DataRepository(database.db)

	# Queries the database for the user
	if includePrivileged and user and user['id'] == userID:
		user = data.getUserByID(userID, includePrivileged=True)
	else:
		user = data.getUserByID(userID)
	# Return a 404 if the user is not found
	if not user:
		raise HTTPException(status_code=404, detail="User not found")

	# Return the user in standard format
	return UserResponse.User(meta={}, data=user)


@router.get('/{userID}/listings', response_model=ListingResponses.Listings)
async def getUserListings(
		userID: str,
		includePrivileged: bool = False,
		user: Dict = Depends(userOptional),
		):
	"""
	Get all listings by a user.
	:param conn: SQL DB connection
	:param userID: A user's id
	:param includePrivileged: Whether to include private information
	:param user:
	:return: 404 or the user's listings
	"""

	data = DataRepository(database.db)

	# Queries the database for the user's listings
	if includePrivileged and user and user['id'] == userID:
		listings = data.getListingsByUserID(userID, includePrivileged=True)
	else:
		listings = data.getListingsByUserID(userID)
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


@router.get('/{userID}/updates')
def getUserStatistics(user=Depends(userRequired)) -> StreamingResponse:
	"""
	Get a user's statistics
	:param user: The user to get statistics for
	:return: A stream of the user's statistics
	"""
	data = DataRepository(database.db)
	endDate = timedelta(weeks=4)
	startDate = datetime.now() - endDate

	def generateStatistics():
		while True:
			yield f'event: userStatsUpdate\ndata: {data.getUserStatistics(user, startDate.strftime('%Y-%m-%d'), 
																		  datetime.now().strftime('%Y-%m-%d'))}\n\n'
			time.sleep(4)

	return StreamingResponse(generateStatistics(), media_type='text/event-stream')
