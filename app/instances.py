"""
Stores shared instances of classes that are used throughout the system.
Isolates shared state.
"""

from app.database import database
from app.functions.search import ListingSearch

listingsSearch = ListingSearch(database.dbQueue)


