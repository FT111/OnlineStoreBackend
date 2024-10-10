import pydantic
import json

from typing import List, Optional, Union, Dict, Any, Tuple, Set

from starlette.requests import Request
from typing_extensions import Annotated
from uuid import uuid4

from app.models.users import User, PrivilegedUser
from app.models.listings import Listing, ListingWithSales, SKU, ListingWithSKUs
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
	print('User:', dict(user))

	if not dict(user):
		return None

	return User(**dict(user))


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
	dbUser['passwordSalt'] = auth.generateSalt()
	dbUser['passwordHash'] = auth.hashPassword(dbUser['password'], dbUser['passwordSalt'])

	Queries.Users.addUser(conn, dbUser)

	return
