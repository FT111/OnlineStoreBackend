import time

import bcrypt
import pydantic
import json

from typing import List, Optional, Union, Dict, Any, Tuple, Set

from starlette.requests import Request
from typing_extensions import Annotated
from uuid import uuid4

from app.models.users import User, PrivilegedUser, UserDetail
from app.models.listings import Listing, ListingWithSales, SKU, ListingWithSKUs, BaseListing
from app.models.categories import Category, SubCategory

from app.database.databaseQueries import Queries
from app.functions import auth


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
	castedListings = []
	for listing in listings:
		listingDict = dict(listing)
		listingDict['ownerUser'] = json.loads(listingDict['ownerUser'])
		listingDict['skus'] = json.loads(listingDict['skus'])
		castedListings.append(listingDict)

	modelListings = [Listing(**dict(listing)) for listing in castedListings]

	return modelListings


def createListing(conn: callable, baseListing: BaseListing, user: User) -> Listing:
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
					  addedAt=int(time.time()),
					  public=False)

	Queries.Listings.addListing(conn, listing)

	return Listing(**dbListing)


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


def getUserByID(conn: callable, userID: str, requestUser: Union[dict, None] = None) -> Union[User, None]:
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


def getListingsByUserID(conn, userID):
	"""
	Get all listings by a user
	:param conn: Database connection
	:param userID: User's ID
	:return: List of listings
	"""

	listings = Queries.Listings.getListingsByUserID(conn, userID)
	castedListings = formatListingRows(listings)

	modelListings = [Listing(**dict(listing)) for listing in castedListings]

	return modelListings


def getListingByID(conn, listingID):
	"""
	Get a listing by its ID
	:param conn: Database connection
	:param listingID: Listing's ID
	:return: Listing
	"""

	listing = Queries.Listings.getListingByID(conn, listingID)
	castedListing = formatListingRows([listing])[0]
	print('Listing:', castedListing)

	modelListing = ListingWithSKUs(**dict(castedListing))

	return modelListing


def formatListingRows(listings):
	castedListings = []
	for listing in listings:
		listingDict = dict(listing)
		listingDict['ownerUser'] = json.loads(listingDict['ownerUser'])
		listingDict['skus'] = json.loads(listingDict['skus'])
		listingDict['skus'] = [SKU(**sku) for sku in listingDict['skus']]
		castedListings.append(listingDict)
	return castedListings
