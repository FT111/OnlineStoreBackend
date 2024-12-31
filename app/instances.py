"""
Stores shared instances of classes that are used throughout the system.
Isolates shared state.
"""

from app.database.database import getDB
from app.functions.search import ListingSearch

listingsSearch = ListingSearch(getDB)


