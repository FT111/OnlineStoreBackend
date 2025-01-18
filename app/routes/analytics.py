from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.functions.data import DataRepository
from app.instances import rateLimiter
from ..database import database
from ..functions.auth import userOptional
from ..models.analytics import Response, Events
from ..models.users import User

"""
These endpoints are blocked by middleware if the user has not consented to analytics
"""
routerPrefix = "/analytics"
router = APIRouter(prefix=routerPrefix, tags=["Analytics"])


@router.post("/{listingID}/click", response_model=Response.ConfirmationResponse)
@rateLimiter.limit("3/minute")
def registerClick(listingID: str,
				  request: Request,
				  user: User = Depends(userOptional)):
	"""
	Register a click on a listing
	Requires analytics consent
	:param request: The request object for rate limiter to hook
	:param listingID:
	:param user:
	:return:
	"""
	data = DataRepository(database.db)

	click: Events.ListingClick = data.registerListingClick(listingID)

	return Response.ConfirmationResponse(meta={
		'registered': True
	},
		data={
			'event': click
		}
	)



