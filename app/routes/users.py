from collections import defaultdict
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from starlette.responses import StreamingResponse

from ..database import database
from ..functions.auth import userRequired, userOptional, generateToken
from ..functions.data import DataRepository
from ..functions.utils import userStatisticsGenerator
from ..instances import emailService, rateLimiter
from ..models.auth import Response as AuthResponse, Token
from ..models.emails import Templates as EmailTemplates
from ..models.listings import Response as ListingResponses
from ..models.users import Response as UserResponse, PwdResetSubmission, PrivilegedUser, UserReviewSubmission
from ..models.users import UserSubmission, PwdResetRequest, PwdResetRequestSubmission

router = APIRouter(prefix="/users", tags=["users"])


@rateLimiter.limit("1/minute")
@router.post('/requestPasswordReset')
def requestPasswordReset(
		resetRequest: PwdResetRequestSubmission,
		request: Request
):
	"""
	Request a password reset email
	:param resetRequest: The request for a password reset
	:param request: The request object
	:return:
	"""

	data = DataRepository(database.db)
	try:
		# Create a password reset request in the data store
		reset: PwdResetRequest = data.createPasswordReset(resetRequest.email)
		# Send an email to the user with the reset link
		emailService.sendEmailTemplate(
			EmailTemplates.PasswordResetEmail(),
			recipientAddress=reset.user.emailAddress,
			username=reset.user.username,
			url=f"{request.url.scheme}://{request.url.hostname}:5173/login/reset/{reset.id}"
		)
	except ValueError as e:
		pass

	return {'data': 'Sent if user exists'}


@router.post('/resetPassword')
def resetPassword(
		reset: PwdResetSubmission
):
	"""
	Reset a user's password
	:param userID: The user's ID
	:param reset: The password reset submission
	:return: 404 or the user
	"""

	data = DataRepository(database.db)

	# Reset the user's password
	data.resetPassword(reset)

	return {'data': 'Password reset'}


@router.get('/me', response_model=UserResponse.PrivilegedUser)
async def getMe(user: Dict = Depends(userRequired),
				):
	"""
	Get the current user
	"""

	data = DataRepository(database.db)

	userDetails = data.getUserByID(user['id'], requestUser=user, includePrivileged=True)

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
	token = generateToken(user.id, user.emailAddress)

	return AuthResponse.Token(meta={}, data=Token(token=token))


@router.post('/{userID}/reviews')
async def submitReview(
		userID: str,
		review: UserReviewSubmission,
		reviewerUser: dict = Depends(userRequired),
):
	"""
	Submit a review for a user
	:param userID: The user to review
	:param review: The review to submit
	:param reviewerUser: The user submitting the review
	:return: 404 or the review
	"""

	data = DataRepository(database.db)

	if reviewerUser['id'] == userID:
		raise HTTPException(status_code=403, detail="Cannot review yourself")

	data.submitUserReview(review, reviewerID=reviewerUser['id'], reviewedID=userID)

	return {'meta': {}, 'data': review}


@router.put('/{userID}', response_model=UserResponse.User)
async def updateUser(
		userID: str,
		user: PrivilegedUser,
	):
	"""
	Update a user in the database.
	Users can only update their own information.
	Could be PUT /me but this is more future-proof.
	:param userID: The user's ID
	:param user: The user to update
	:return: 404 or the user
	"""

	if userID != user.id:
		raise HTTPException(status_code=403, detail="Cannot update another user's account")

	data = DataRepository(database.db)

	user = data.updateUser(user)

	return UserResponse.User(meta={}, data=user)


@router.get('/{userID}')
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
	return {'meta': {}, 'data': user}


@router.get('/{userID}/reviews')
async def getUserReviews(
		userID: str,
):
	"""
	Get all user reviews that the user is recipient of
	:param userID: The user's id
	:return: 404 or the user's reviews
	"""

	data = DataRepository(database.db)

	# Check if the user exists
	user = data.getUserByID(userID)
	if not user:
		raise HTTPException(status_code=404, detail="User not found")

	# Queries the database for the user's reviews
	reviews = data.getUserReviews(user)

	# Return the user's reviews in standard format
	return {'meta': {}, 'data': reviews}


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


@router.get('/{userID}/orders')
def getUserOrders(
		userID: str,
		user=Depends(userRequired),
):
	"""
	Get all orders by a user
	:param user: The authenticated user
	:param userID: The user's id
	:return: The user's orders
	"""

	if user['id'] != userID:
		raise HTTPException(status_code=403, detail="Cannot retrieve another user's orders")

	data = DataRepository(database.db)

	orders = data.getOrdersByUserID(userID)

	return {'data': orders}


@router.get('/{userID}/updates')
def getUserUpdates(user=Depends(userRequired)) -> StreamingResponse:
	"""
	Get a user's statistics
	:param user: The user to get statistics for
	:return: A stream of the user's statistics
	"""
	data = DataRepository(database.db)

	return StreamingResponse(userStatisticsGenerator(data, user), media_type='text/event-stream')


@router.get('/me/statistics/{fromDate}/{toDate}')
def getUserStatistics(
		fromDate: str,
		toDate: str,
		user=Depends(userRequired),
):
	"""
	Get a user's statistics over a given period
	:param user: The user to get statistics for
	:param userID: The user's id
	:param fromDate: The start date for the statistics
	:param toDate: The end date for the statistics
	"""
	data = DataRepository(database.db)

	# Validate the dates
	try:
		datetime.strptime(fromDate, '%Y-%m-%d')
		datetime.strptime(toDate, '%Y-%m-%d')
	except ValueError:
		raise HTTPException(status_code=400, detail="Invalid date format")

	stats: dict = data.getUserStatistics(user, fromDate, toDate)

	return {'data': stats}
