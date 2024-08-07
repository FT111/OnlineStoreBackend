
import pydantic
import json

from typing import List, Optional, Union, Dict, Any, Tuple, Set
from typing_extensions import Annotated

from app.models.users import User, PrivilegedUser, DatabaseUser
from app.models.listings import Listing, ListingWithSales, SKU, ListingWithSKUs
from app.models.categories import Category, SubCategory

from app.database.databaseQueries import Queries


def idsToListings(conn: callable, listingIDs: list) -> List[Listing]:
    """
    Get a listing by its ID

    Args:
    conn: The connection to the database
    listingID: The ID of the listing

    Returns:
    The listing with the given ID
    """

    listings = Queries.getListingsByIDs(conn, listingIDs)
    castedListings = []
    for listing in listings:
        listingDict = dict(listing)
        listingDict['ownerUser'] = json.loads(listingDict['ownerUser'])
        listingDict['skus'] = json.loads(listingDict['skus'])
        castedListings.append(listingDict)

    for listing in castedListings:
        print(f"Category: {listing['category']}, SubCategory: {listing['subCategory']}")
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

    castedCategories = []
    modelCategories = []
    for category in categories:
        categoryDict = dict(category)
        categoryDict['subCategories'] = json.loads(categoryDict['subCategories'])
        castedCategories.append(categoryDict)

    for category in castedCategories:
        modelCategories = [Category(**dict(category)) for category in castedCategories]

    return modelCategories


