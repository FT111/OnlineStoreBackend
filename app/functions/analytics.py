import time
from uuid import uuid4

from fastapi import Request
from typing_extensions import List, Optional

from app.models.analytics import Events


class Impressions:
	@staticmethod
	def retrieveImpressionsFromRequest(request: Request, user: Optional[dict]) -> List[
		Optional[Events.ListingImpression]]:
		"""
		Retrieves the impressions from the request
		Links to given user ID if provided
		"""
		impressions = request.cookies.get('impressions')
		if impressions is None:
			return []

		impressions = impressions.split(',')
		impressions = [Events.ListingImpression(
			id=str(uuid4()),
			userID=user['id'] if user else None,
			listingID=listingID,
			time=int(time.time()),
			userIP=request.client.host
		) for listingID in impressions]

		return impressions
