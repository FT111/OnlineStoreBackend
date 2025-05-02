import sqlite3

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response, JSONResponse

from app.database import database
from app.functions.analytics import Impressions
from app.functions.auth import validateToken
from app.functions.data import DataRepository
from app.routes.analytics import routerPrefix as analyticsRouterPrefix


class HandleAnalyticsMiddleware(BaseHTTPMiddleware):
	"""
	Middleware for handling analytics
	Needs to run after a user has been added to the request state
	"""

	async def dispatch(
			self, request: Request, call_next: RequestResponseEndpoint,

	) -> Response:

		# If the request is an OPTIONS request, return the response prior to processing
		if request.method == 'OPTIONS':
			return await call_next(request)

		# If the user has not consented to analytics, return the response prior to processing
		if request.headers.get('x-analytics-consent') != 'true':

			# Gates analytics processing endpoints
			if request.url.path.startswith(analyticsRouterPrefix):
				return JSONResponse(status_code=403, content={'detail': 'Analytics consent required'})

			response = await call_next(request)
			return response

		# --v---v---v--- If the user has consented to analytics, process the request --v---v---v---v---v---v---v---v-

		data = DataRepository(database.db)
		print(request.cookies)

		# Retrieve the impressions from the request
		while True:
			try:
				impressions = Impressions.retrieveImpressionsFromRequest(request, getattr(request.state, 'user', None))
				if not impressions:
					break

				# Add the impressions to the database
				data.registerListingEvents(impressions)
				break
			except sqlite3.IntegrityError:
				break

		response = await call_next(request)
		response.set_cookie('impressions', '', max_age=0)
		return response


class GetUserMiddleware(BaseHTTPMiddleware):
	"""
	Checks for a JWT token in the request header, validates it, and adds the user to the request state
	"""

	async def dispatch(self, request: Request, call_next):

		# Get the bearer header from the request
		# The american spelling because it's the standard for JWT :(
		authHeader = request.headers.get('Authorization')

		# Get the JWT token from the header
		JWT = authHeader.split(' ')[1] if authHeader else None

		# Validates the token if it exists, returns the user if valid
		if JWT:
			user = validateToken(JWT)
			if user:
				request.state.user = user
			else:
				request.state.user = None
		else:
			request.state.user = None

		# Continue the request
		response = await call_next(request)

		# Return the response
		return response
