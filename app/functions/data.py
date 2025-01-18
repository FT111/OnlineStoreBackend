import base64
import json
import time
from typing import List, Union
from uuid import uuid4

import bcrypt
import pydantic
from fastapi import HTTPException
from typing_extensions import Optional

from app.database.databaseQueries import Queries
from app.functions import auth
from app.models.analytics import Events
from app.models.categories import Category
from app.models.listings import Listing, ListingWithSales, ListingWithSKUs, ListingSubmission, SKUWithStock, \
	SKUSubmission, SKU
from app.models.transactions import Basket, EnrichedBasket
from app.models.users import User, PrivilegedUser, UserDetail


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
					includePrivileged: bool = False) -> Union[User, None]:
		"""
		Get a user by their ID

		Args:
		conn: The connection to the database
		userID: The ID of the user

		Returns:
		The user with the given ID
		"""

		user = Queries.Users.getUserByID(self.conn, userID)

		if not dict(user):
			return None

		user = dict(user)
		user['listingIDs'] = json.loads(user['listingIDs'])

		return UserDetail(**user)

	def createUser(self,
				   user: PrivilegedUser):
		"""
		Adds a user to the database
		:param user: User Pydantic model, assumed to be valid
		:return:
		"""

		dbUser = dict(user)
		dbUser['id'] = str(uuid4())

		# Hash the password and store the salt
		salt = bcrypt.gensalt().decode('utf-8')
		dbUser['passwordSalt'] = salt
		passwordHash = auth.hashPassword(dbUser['password'], salt)

		# Remove the plaintext password and store the hash
		dbUser['passwordHash'] = passwordHash
		del dbUser['password']

		dbUser['joinedAt'] = int(dbUser['joinedAt'])

		# Add the user to the database
		Queries.Users.addUser(self.conn, dbUser)

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

		modelListings = [Listing(**dict(listing)) for listing in castedListings]

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

		sku.images = self.processAndStoreImages(sku.images, sku.id)

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
		sku.images = self.processAndStoreImages(fullSKU.images, fullSKU.id)
		Queries.Listings.addSKU(self.conn, fullSKU, listingID)

		return fullSKU

	@staticmethod
	def processAndStoreImages(images: list, uniqueID) -> list:
		# Save new images to the filesystem
		for index, image in enumerate(images):
			# If the image is a base64 string, save it to the filesystem
			if image.startswith('data:image'):
				# Remove the base64 header
				image = image.split('base64,')[1]

				# Save the image to the filesystem
				filename = f"sku-{uniqueID}-{index + 1}.jpeg"
				with open(f"app/static/listingImages/{filename}", 'wb') as file:
					file.write(base64.decodebytes(image.encode('utf-8')))
				images[index] = filename
				continue

			# If the image is an existing filepath, keep it
			if image.startswith('sku-'):
				continue

			# Remove the image if it isn't a base64 string or filepath
			print(f"Invalid image: {image}")
			del images[index]

		return images

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
		listingDict: dict[str, dict] = {}
		for listing in castedListings:
			for sku in listing['skus']:
				listingDict[sku.id] = listing

		# Transform SKU ids to full SKU objects, from the listing
		for skuID in basket.items:
			basket.items[skuID]['sku'] = [sku for sku in listingDict[skuID]['skus'] if sku.id == skuID][0]

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

	def registerListingClick(self, listingID, userID: Optional[str] = None):
		"""
		Register a click on a listing
		:param userID: The ID of the user clicking the listing, if logged in
		:param listingID:
		:return:
		"""

		while True:
			click = Events.ListingClick(
				id=str(uuid4()),
				userID=userID,
				listingID=listingID,
				time=int(time.time())

			)

			# Attempt to register the event
			# If the event id already exists, generate a new ID and try again
			# Handles the incredibly unlikely event of a UUID collision
			try:
				Queries.Analytics.registerEvent(self.conn, click)
				break
			except NameError:
				continue

		return click




