import base64
import json
import time
from typing import List, Union
from uuid import uuid4

import bcrypt
import pydantic
from fastapi import HTTPException

from app.database.databaseQueries import Queries
from app.functions import auth
from app.models.categories import Category
from app.models.listings import Listing, ListingWithSales, ListingWithSKUs, ListingSubmission, SKUWithStock, \
	SKUSubmission
from app.models.users import User, PrivilegedUser, UserDetail


def idsToListings(conn: callable, listingIDs: list) -> List[Listing]:
	"""
	Get a listing by its ID

	Args:
	conn: The connection to the database
	listingID: The ID of the listing

	Returns:
	The listing with the given ID
	"""

	listings = Queries.Listings.getListingsByIDs(conn, listingIDs)

	return formatListingRows(listings)


def createListing(conn: callable, baseListing: ListingSubmission, user: User) -> Listing:
	"""
	Adds a listing to the database
	:param conn: Database connection
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

	Queries.Listings.addListing(conn, listing)

	return listing


def getAllCategories(conn: callable) -> List[Category]:
	"""
	Get all categories

	Args:
	conn: The connection to the database

	Returns:
	All categories
	"""

	categories = Queries.Categories.getAllCategories(conn)

	modelCategories = [
		Category(**dict({**category, 'subCategories': json.loads(category['subCategories'])}))
		for category in categories
	]

	return modelCategories


def getCategory(conn: callable, title: str) -> Category:
	"""
	Gets a single category
	:param title:
	:param conn:
	:return:
	"""
	category = Queries.Categories.getCategory(conn, title)
	category = Category(**dict({**category, 'subCategories': json.loads(category['subCategories'])}))

	return category


def getUserByID(conn: callable, userID: str,
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

	user = Queries.Users.getUserByID(conn, userID)

	if not dict(user):
		return None

	user = dict(user)
	user['listingIDs'] = json.loads(user['listingIDs'])
	print('User:', user)

	return UserDetail(**user)


def createUser(conn: callable,
			   user: PrivilegedUser):
	"""
	Adds a user to the database
	:param conn: Database connection
	:param user: User Pydantic model, assumed to be valid
	:return:
	"""

	dbUser = dict(user)
	dbUser['id'] = str(uuid4())
	salt = bcrypt.gensalt().decode('utf-8')
	dbUser['passwordSalt'] = salt
	passwordHash = auth.hashPassword(dbUser['password'], salt)
	dbUser['passwordHash'] = passwordHash
	del dbUser['password']
	dbUser['joinedAt'] = int(dbUser['joinedAt'])

	print('DB User:', dbUser)
	Queries.Users.addUser(conn, dbUser)

	return PrivilegedUser(**dbUser)


def getListingsByUserID(conn, userID, includePrivileged=False):
	"""
	Get all listings by a user
	:param includePrivileged: Whether to include private information
	:param conn: Database connection
	:param userID: User's ID
	:return: List of listings
	"""

	listings = Queries.Listings.getListingsByUserID(conn, userID, includePrivileged=includePrivileged, )
	castedListings = formatListingRows(listings)

	modelListings = [Listing(**dict(listing)) for listing in castedListings]

	return modelListings


def getListingByID(conn, listingID,
				   includePrivileged=False, user: Union[User, None] = None):
	"""
	Get a listing by its ID
	:param includePrivileged:
	:param user:
	:param conn: Database connection
	:param listingID: Listing's ID
	:return: Listing
	"""

	listing = None
	if not includePrivileged:
		listing = Queries.Listings.getListingByID(conn, listingID)
	elif user is not None:
		listing = Queries.Listings.getListingByID(conn, listingID, includePrivileged=True, requestUserID=user['id'])

	if listing is None:
		raise NameError(f'Listing with id \'{listingID}\' not found')

	castedListing = formatListingRows([listing])[0]

	if not includePrivileged:
		modelListing = ListingWithSKUs(**dict(castedListing))
	else:
		modelListing = ListingWithSales(**dict(castedListing))

	return modelListing


def updateListing(conn, listing: ListingWithSKUs):
	"""
	Update a listing
	:param conn: Database connection
	:param listing: Listing Pydantic model
	:return:
	"""

	Queries.Listings.updateListing(conn, listing)

	return listing


def updateSKU(conn1, conn2, sku: SKUWithStock, listingID: str):
	"""
	Update a SKU
	:param conn1: Database connection
	:param conn2: Database connection for the SKU
	:param sku: SKU Pydantic model
	:param listingID: The ID of the listing the SKU belongs to
	:return:
	"""

	sku.images = processAndStoreImages(sku.images, sku.id)

	# Check if the SKU already exists with the same options - Must be unique
	if len(sku.options) > 0:
		existingSKU = Queries.Listings.getSKUByOptions(conn1, sku.options, listingID)

		# If the SKU exists and is not the same as the current SKU, raise a conflict
		if existingSKU and existingSKU['id'] != sku.id:
			raise HTTPException(status_code=409, detail="SKU with these options already exists")

	Queries.Listings.updateSKU(conn2, sku)

	return sku


def createSKU(conn, sku: SKUSubmission, listingID: str) -> SKUWithStock:
	"""
	Create a SKU
	:param conn: Database connection
	:param sku: SKU Pydantic model
	:param listingID: The ID of the listing to add the SKU to
	:return:
	"""

	fullSKU = SKUWithStock(**dict(sku), id=str(uuid4()))
	sku.images = processAndStoreImages(fullSKU.images, fullSKU.id)
	Queries.Listings.addSKU(conn, fullSKU, listingID)

	return fullSKU


def processAndStoreImages(images: list, uniqueID) -> list:
	# Save new images to the filesystem
	for index, image in enumerate(images):
		# If the image is a base64 string, save it to the filesystem
		if image.startswith('data:image'):
			# Remove the base64 header
			image = image.split('base64,')[1]

			# Save the image to the filesystem
			filename = f"sku-{uniqueID}-{index+1}.jpeg"
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
