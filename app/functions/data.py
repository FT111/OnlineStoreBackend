import json
import json
import sqlite3
import time
from uuid import uuid4

import bcrypt
import pydantic
from fastapi import HTTPException
from typing_extensions import List, Union, Dict
from typing_extensions import Optional, Type

from app.database.databaseQueries import Queries
from app.functions import auth
from app.functions.utils import dateRangeGenerator, processAndStoreImagesFromBase64
from app.models.analytics import Events
from app.models.categories import Category
from app.models.listings import Listing, ListingWithSales, ListingWithSKUs, ListingSubmission, SKUWithStock, \
	SKUSubmission, SKU, SKUWithUser, ShortListing, ListingReview, ListingReviewSubmission
from app.models.transactions import Basket, EnrichedBasket, UserOrders, Order, SKUPurchase, InternalPurchase
from app.models.users import User, PrivilegedUser, UserDetail, PwdResetRequest, PwdResetSubmission, UserReview, \
	UserReviewSubmission


class DataRepository:
	"""
	Handles all data operations

	Wraps database queries and formats the inputs/results

	Must be instantiated to define the database connection
	"""

	def __init__(self, connection):
		self.conn = connection

	def idsToListings(self,
					  listingIDs: list) -> List[Listing]:
		"""
		Get a listing by its ID

		Args:
		conn: The connection to the database
		listingID: The ID of the listing

		Returns:
		The listing with the given ID
		"""

		listings = Queries.Listings.getListingsByIDs(self.conn, listingIDs)

		return self.formatListingRows(listings)

	def createListing(self,
					  baseListing: ListingSubmission,
					  user: User) -> Listing:
		"""
		Adds a listing to the database
		:param baseListing: Basic User Pydantic model
		:param user: The user creating the listing
		:return:
		"""

		# Prepares the listing for the database
		listing = Listing(**dict(baseListing),
						  ownerUser=user,
						  id=str(uuid4()),
						  views=0,
						  rating=0,
						  addedAt=int(time.time())
						  )

		Queries.Listings.addListing(self.conn, listing)

		return listing

	def getAllCategories(self) -> List[Category]:
		"""
		Get all categories

		Args:
		conn: The connection to the database

		Returns:
		All categories
		"""

		categories = Queries.Categories.getAllCategories(self.conn)

		modelCategories = [
			Category(**dict({**category, 'subCategories': json.loads(category['subCategories'])}))
			for category in categories
		]

		return modelCategories

	def getCategory(self, title: str) -> Category:
		"""
		Gets a single category
		:param title:
		:return:
		"""
		category = Queries.Categories.getCategory(self.conn, title)
		if not category:
			raise HTTPException(status_code=404, detail="Category not found")
		category = Category(**dict({**category, 'subCategories': json.loads(category['subCategories'])}))

		return category

	def getUserByID(self, userID: str,
					requestUser: Union[dict, None] = None,
					includePrivileged: bool = False) -> Union[User, PrivilegedUser, None]:
		"""
		Get a user by their ID

		Args:
		conn: The connection to the database
		userID: The ID of the user

		Returns:
		The user with the given ID
		"""

		user = Queries.Users.getUserByID(self.conn, userID)

		if not user:
			return None

		try:
			user = dict(user)
			user['listingIDs'] = json.loads(user['listingIDs'])
			modelUser = PrivilegedUser(**user) if includePrivileged else UserDetail(**user)
		except pydantic.ValidationError:
			return None

		return modelUser

	def createUser(self,
				   user: PrivilegedUser):
		"""
		Adds a user to the database
		:param user: User Pydantic model, already validated
		:return:
		"""

		dbUser = dict(user)
		dbUser['id'] = str(uuid4())

		# Hash the password and store the salt
		salt = bcrypt.gensalt()
		dbUser['passwordSalt'] = salt.decode('utf-8')
		passwordHash = auth.hashPassword(dbUser['password'], salt)

		# Remove the plaintext password and store the hash
		dbUser['passwordHash'] = passwordHash
		del dbUser['password']

		dbUser['joinedAt'] = int(dbUser['joinedAt'])

		# Add the user to the database
		try:
			Queries.Users.addUser(self.conn, dbUser)
		except sqlite3.IntegrityError:
			raise HTTPException(status_code=409, detail="Email or username are already in use")

		return PrivilegedUser(**dbUser)

	def getListingsByUserID(self, userID, includePrivileged=False):
		"""
		Get all listings by a user
		:param includePrivileged: Whether to include private information
		:param userID: User's ID
		:return: List of listings
		"""

		listings = Queries.Listings.getListingsByUserID(self.conn, userID, includePrivileged=includePrivileged, )
		castedListings = self.formatListingRows(listings)
		listingModel = ListingWithSales if includePrivileged else Listing

		modelListings = [listingModel(**dict(listing)) for listing in castedListings]

		return modelListings

	def getListingByID(self, listingID,
					   includePrivileged=False, user: Union[User, None] = None):
		"""
		Get a listing by its ID
		:param includePrivileged:
		:param user:
		:param listingID: Listing's ID
		:return: Listing
		"""

		listing = None
		if not includePrivileged:
			listing = Queries.Listings.getListingByID(self.conn, listingID)
		elif user is not None:
			listing = Queries.Listings.getListingByID(self.conn, listingID, includePrivileged=True,
													  requestUserID=user['id'])

		if listing is None:  # If the listing is not found, raise a 404
			raise HTTPException(status_code=404, detail="Listing not found")

		castedListing = self.formatListingRows([listing])[0]

		if not includePrivileged:
			modelListing = ListingWithSKUs(**dict(castedListing))
		else:
			modelListing = ListingWithSales(**dict(castedListing))

		return modelListing

	def updateListing(self, listing: ListingWithSKUs):
		"""
		Update a listing
		:param listing: Listing Pydantic model
		:return:
		"""

		Queries.Listings.updateListing(self.conn, listing)

		return listing

	def updateSKU(self, sku: SKUWithStock, listingID: str):
		"""
		Update a SKU
		:param sku: SKU Pydantic model
		:param listingID: The ID of the listing the SKU belongs to
		:return:
		"""

		sku.images = processAndStoreImagesFromBase64(sku.images, sku.id, 'sku')

		# Check if the SKU already exists with the same options - Must be unique
		if len(sku.options) > 0:
			existingSKU = Queries.Listings.getSKUByOptions(self.conn, sku.options, listingID)

			# If the SKU exists and is not the same as the current SKU, raise a conflict
			if existingSKU and existingSKU['id'] != sku.id:
				raise HTTPException(status_code=409, detail="SKU with these variation options already exists")

		Queries.Listings.updateSKU(self.conn, sku)

		return sku

	def createSKU(self, sku: SKUSubmission, listingID: str) -> SKUWithStock:
		"""
		Create a SKU
		:param sku: SKU Pydantic model
		:param listingID: The ID of the listing to add the SKU to
		:return:
		"""

		fullSKU = SKUWithStock(**dict(sku), id=str(uuid4()))
		sku.images = processAndStoreImagesFromBase64(fullSKU.images, fullSKU.id, 'sku')
		Queries.Listings.addSKU(self.conn, fullSKU, listingID)

		return fullSKU

	@staticmethod
	def formatListingRows(listings):
		"""
		Formats listings from the database into a usable dictionary from JSON
		:param listings: List of listings
		:return:
		"""
		if not listings:
			return []
		if listings[0] is None:
			return []

		conversions = ['ownerUser', 'images', 'skuOptions']

		castedListings = []
		for listing in listings:
			listingDict = dict(listing)

			# Convert JSON strings from SQL to dictionaries
			for key in conversions:
				listingDict[key] = json.loads(listingDict[key])

			# Convert the SKUs from JSON to a list of SKU objects
			# Uses the SKUWithStock model to store the most detail
			# Can be converted to a SKU model if needed
			try:
				listingDict['skus'] = [SKUWithStock(**sku) for sku in json.loads(listingDict['skus'])]
			except pydantic.ValidationError:
				# If the SKUs are invalid, return an empty list
				# Handles the database returning a single invalid SKU if none are present
				listingDict['skus'] = []

			# listingDict['skus'] = [dict(**sku) for sku in listingDict['skus']]
			castedListings.append(listingDict)
		return castedListings

	@staticmethod
	def parseSKUs(skus: List[sqlite3.Row]) -> List[SKU]:
		"""
		Parse a list of SKUs from the database
		:param skus: List of sqlite3.Row objects
		:return:
		"""

		parsedRows = ['options', 'images', 'ownerUser']
		skus = [dict(sku) for sku in skus]
		skus = [SKUWithUser(**{key: json.loads(sku[key]) if key in parsedRows else sku[key] for key in sku})
				for sku in skus]

		return skus

	def getCategoryBySubcategoryTitle(self, subcategoryTitle) -> Optional[Category]:
		"""
		Get a category by its subcategory title
		:param conn: Database connection
		:param subcategoryTitle: Subcategory title
		:return: Category
		"""

		# Attempts to retrieve the category from the database
		category = Queries.Categories.getCategoryBySubcategoryTitle(self.conn, subcategoryTitle)
		if not category:
			return None

		# Converts returned row to a Category model
		category = Category(**dict({**category, 'subCategories': json.loads(category['subCategories'])}))

		return category

	def enrichBasket(self, basket: Basket) -> EnrichedBasket:
		"""
		Enrich a basket with associated SKUs and listings
		Transforms a basket of SKU IDs into a basket of full SKU objects
		:param basket:
		:return:
		"""
		# Get the SKUs from the database
		skuIDs = list(basket.items.keys())
		listings = Queries.Listings.getListingsBySKUids(self.conn, skuIDs)
		castedListings = self.formatListingRows(listings)

		# Transform listings to dict<relevantskuID, Listing>
		listingDict: Dict[str, dict] = {}
		for listing in castedListings:
			for sku in listing['skus']:
				listingDict[sku.id] = listing

		# Transform SKU ids to full SKU objects, from the listing
		for skuID in basket.items:
			basket.items.get(skuID, None)['sku'] = [sku for sku in listingDict.get(skuID, None)['skus'] if sku.id == skuID][0]

		# Convert to EnrichedBasket model
		enrichedBasket = EnrichedBasket(
			items={
				skuID: {
					'quantity': basket.items[skuID]['quantity'],
					'sku': SKU(**dict(basket.items[skuID]['sku'])),
					'listing': Listing(**listingDict[skuID])
				}
				for skuID in basket.items
			}
		)

		return enrichedBasket

	def registerListingEvent(self, eventType: Type[Events.Event], listingID, userID: Optional[str] = None,
							 userIP: str = 'localhost') -> Type[Events.Event]:
		"""
		Register a click on a listing
		:param userIP: The IP address of the user that clicked the listing
		:param eventType: The type of event to register
		:param userID: The ID of the user that clicked the listing, if logged in
		:param listingID:
		:return:
		"""

		while True:
			event = eventType(
				id=str(uuid4()),
				userID=userID,
				listingID=listingID,
				time=int(time.time()),
				userIP=userIP

			)

			# Attempt to register the event
			# If the event id already exists, generate a new ID and try again
			# Handles the incredibly unlikely event of a UUID collision
			try:
				Queries.Analytics.registerEvent(self.conn, event)
				break
			except sqlite3.IntegrityError:
				print('It finally happened')
				continue

		return event

	def registerListingEvents(self, events: List[Type[Events.Event]]) -> List[Type[Events.Event]]:
		"""
		Register multiple events
		:param events: List of events
		:return:
		"""

		Queries.Analytics.registerEvents(self.conn, events)

		return events

	def getUserStatistics(self, user: User, start: str, end: str) -> dict:
		"""
		Get a user's statistics between two dates
		:param user: User dict
		:param start: ISO8601 date string. i.e '2025-00-25'
		:param end: ISO8601 date string
		:return:
		"""

		statsWithoutEmptyDates = {row['eventType']: {'count': row['count'], 'events': json.loads(row['events'])}
				 for row in Queries.Users.getUserStatistics(self.conn, user['id'], start, end)}
		stats = {}

		for eventType in statsWithoutEmptyDates:
			filledEvents = []
			for date in dateRangeGenerator(start, end):
				for event in [event for event in statsWithoutEmptyDates[eventType]['events'] if event['date'] == date]:
					filledEvents.append(event)
					break
				else:
					filledEvents.append({'date': date, 'count': 0})

			stats[eventType] = {
				'count': statsWithoutEmptyDates[eventType]['count'],
				'events': filledEvents
			}
		# clicks = [row['count'] for row in stats if row['eventType'] == 'click'][0]
		# impressions = [row['count'] for row in stats if row['eventType'] == 'impression'][0]
		# stats.append({'eventType': 'clickThroughRate', 'value': clicks/impressions})

		return stats

	def updateUser(self, user: PrivilegedUser):
		"""
		Update a user
		:param user: User Pydantic model
		:return:
		"""

		if user.profilePictureURL: user.profilePictureURL = processAndStoreImagesFromBase64(user.profilePictureURL, user.id,
																							'profile', 'user-profiles')
		if user.bannerURL: user.bannerURL = processAndStoreImagesFromBase64(user.bannerURL, user.id,
																			'banner', 'user-profiles')

		try:
			Queries.Users.updateUser(self.conn, user)
		except sqlite3.IntegrityError:
			raise HTTPException(status_code=409, detail="Email or username are already in use")

		return user

	def getAllConditions(self):
		"""
		Get all wear conditions
		:return:
		"""

		conditions = Queries.Listings.getAllConditions(self.conn)
		conditions = [str(condition['title']) for condition in conditions]
		return conditions

	def createPasswordReset(self, emailAddress) -> PwdResetRequest:
		"""
		Create a password reset request
		:param emailAddress: Email address of the user
		:return:
		"""

		user = Queries.Users.getUserByEmail(self.conn, emailAddress)
		if not user:
			raise ValueError('User not found')

		requestId = str(uuid4())
		hashedId = auth.hashValue(requestId)
		reset: PwdResetRequest = PwdResetRequest(
			id=requestId,
			hashedId=hashedId,
			user=PrivilegedUser(**dict(user)),
			addedAt=int(time.time())
		)

		Queries.Users.createPasswordReset(self.conn, reset)

		return reset

	def resetPassword(self, reset: PwdResetSubmission):
		"""
		Reset a user's password
		:param reset: Password reset submission object
		:return:
		"""

		# Hash the token, as it is stored in the database
		hashedId = auth.hashValue(reset.token)

		# Check if the reset request exists
		existingResetRequest = Queries.Users.getPasswordReset(self.conn, hashedId)
		if not existingResetRequest:
			raise HTTPException(status_code=404, detail="Reset request not found")
		existingResetRequest = existingResetRequest[0]

		# Check if the reset request is expired
		if existingResetRequest['addedAt'] < time.time() - 1800:
			raise HTTPException(status_code=400, detail="Reset request expired")

		# Ensure the user exists
		user = Queries.Users.getUserByID(self.conn, existingResetRequest['userID'])
		if not user:
			raise HTTPException(status_code=404, detail="User not found")

		# Hash the password and store the salt
		passwordHash = auth.hashPassword(reset.password, auth.generateSalt())

		# Update the user's password
		Queries.Users.updatePassword(self.conn, user['id'], passwordHash)

		# Delete the reset request
		Queries.Users.deletePasswordReset(self.conn, hashedId)

	def idsToSKUs(self, skuIDs, desiredObj: SKU) -> list:
		"""
		Get a SKU by its ID
		:param skuIDs: List of SKU IDs
		:param desiredObj: The type of SKU object needed
		:return:
		"""

		skus: List[sqlite3.Row] = Queries.Listings.getSKUsByIDs(self.conn, skuIDs)
		skus: List[SKU] = [desiredObj(**dict(sku)) for sku in self.parseSKUs(skus)]

		return skus

	def addOrder(self, order):
		"""
		Add an order to the database
		:param order: Order object
		:return:
		"""

		Queries.Transactions.addOrder(self.conn, order)
		Queries.Transactions.addToUserBalance(self.conn, order.seller.id, order.value)

	def updateSKUStock(self, id, stock):
		"""
		Update the stock of a SKU to a given value
		:param id:
		:param stock:
		:return:
		"""

		Queries.Listings.updateSKUStock(self.conn, id, stock)

	def getOrdersByUserID(self, id):
		"""
		Get all orders by a user.
		Split into sales and purchase orders
		:param id: User's ID
		:return:
		"""

		# Get the user's orders from the database
		orders = dict(
			sales=Queries.Transactions.getSaleOrdersByUserID(self.conn, id),
			purchases=Queries.Transactions.getPurchaseOrdersByUserID(self.conn, id)
		)

		# Convert the orders to Order objects and calculate the order value
		for orderType in orders:

			# Loops through each order
			for index, order in enumerate(orders[orderType]):
				order = dict(order)
				order['value'], order['quantity'] = 0, 0

				# Convert SKU JSON to SKU objects
				order['skus'] = json.loads(order['skus'])
				# Loop through each product SKU in the order
				for i, sku in enumerate(order['skus']):

					# Add to the overall order value
					order['value'] += sku['price']

					# Convert the SKU to an SKUPurchase object with the listing
					order['skus'][i] = SKUPurchase(
						sku=SKU(**dict(sku)),
						listing=ShortListing(**dict(sku['listing'])),
						quantity=sku.get('quantity'),
						value=sku.get('price')
					)

				order['recipient'] = json.loads(order['recipient']) if order.get('recipient') else None
				order['seller'] = json.loads(order['seller']) if order.get('seller') else None

				# Convert the order to an Order object
				orders[orderType][index] = Order(**order)

		orders = UserOrders(**orders)

		return orders

	def getOrderByID(self, orderID) -> Order:
		"""
		Get an order by its ID
		:param orderID:
		:return:
		"""

		order = Queries.Transactions.getOrder(self.conn, orderID)
		if not order:
			raise HTTPException(status_code=404, detail="Order not found")

		order = dict(order)
		order['skus'] = json.loads(order['skus'])
		order['value'] = 0

		# Convert the SKUs to SKUPurchase objects
		for i, sku in enumerate(order['skus']):
			order['skus'][i] = SKUPurchase(
				sku=SKU(**dict(sku)),
				listing=ShortListing(**dict(sku['listing'])),
				quantity=sku.get('quantity'),
				value=sku.get('price')
			)
			order['value'] += sku['price']

		order['recipient'] = json.loads(order['recipient']) if order.get('recipient') else None
		order['seller'] = json.loads(order['seller']) if order.get('seller') else None

		order = Order(**order)

		return order

	def updateOrderStatus(self, order, status):
		"""
		Update an order's status and subtract from the seller's balance if cancelled
		:param order: Order object
		:param status:
		:return:
		"""

		updateTime = int(time.time())
		Queries.Transactions.updateOrderStatus(self.conn, order.id, status, updateTime)

		if status == 'CANCELLED':
			# 		Remove the order from the user's balance
			Queries.Transactions.subtractFromUserBalance(self.conn, order.seller.id, order.value, True)

	def addPurchase(self, purchase: InternalPurchase):
		"""
		Add a purchase to the database
		:param purchase:
		:return:
		"""

		Queries.Transactions.addPurchase(self.conn, purchase)

	def addReview(self, review: ListingReviewSubmission, userID: str):
		"""
		Add a review to the database
		:param userID:
		:param review:
		:return:
		"""

		userListings = Queries.Listings.getListingsByUserID(self.conn, userID, includePrivileged=True)
		if review.listingID in [listing['id'] for listing in userListings]:
			raise HTTPException(status_code=403, detail="You cannot review your own listing")

		if not Queries.Listings.getListingByID(self.conn, review.listingID):
			raise HTTPException(status_code=404, detail="Listing not found")

		for review in Queries.Listings.getListingReviews(self.conn, review.listingID):
			if review['userID'] == userID:
				raise HTTPException(status_code=409, detail="You have already reviewed this listing")

		reviewID = str(uuid4())

		Queries.Listings.addListingReview(self.conn, review, reviewID, userID)

	def getListingReviews(self, listingID) -> List[ListingReview]:
		"""
		Get all reviews for a listing
		:param listingID:
		:return:
		"""

		reviews = Queries.Listings.getListingReviews(self.conn, listingID)
		castedReviews = []
		for review in reviews:
			try:
				castedReviews.append(dict(review))
				castedObj = castedReviews[len(castedReviews)-1]
				castedObj['reviewer'] = json.loads(review['user'])
				castedObj['listingID'] = listingID
				castedReviews[len(castedReviews)-1] = ListingReview(**castedReviews[len(castedReviews)-1])
			except pydantic.ValidationError:
				castedReviews.pop()
				continue

		return castedReviews

	def getUserReviews(self, user: User) -> List[UserReview]:
		"""
		Get all reviews for a user
		:param user:
		:return:
		"""

		reviews = Queries.Users.getUserReviews(self.conn, user)
		castedReviews = []
		for review in reviews:
			try:
				castedReviews.append(dict(review))
				castedObj = castedReviews[len(castedReviews)-1]
				castedObj['reviewer'] = json.loads(review['reviewer'])
				castedReviews[len(castedReviews)-1] = UserReview(**castedReviews[len(castedReviews)-1])
			except pydantic.ValidationError:
				castedReviews.pop()
				continue

		return castedReviews

	def submitUserReview(self, review: UserReviewSubmission,
						 reviewerID: str, reviewedID: str,
						 ) -> None:
		"""
		Submit a review for a user
		:param review:
		:param reviewerID:
		:param reviewedID:
		:return: None or HTTP Exception
		"""

		if not Queries.Users.getUserByID(self.conn, reviewedID):
			raise HTTPException(status_code=404, detail="User not found")

		reviewID = str(uuid4())
		return Queries.Users.addUserReview(self.conn, review, reviewID, reviewerID, reviewedID)
