"""
Stores shared instances of classes that are used throughout the system.
Isolates shared state.
"""

from slowapi import Limiter, util

from app.database import database
from app.functions.search import ListingSearch

listingsSearch = ListingSearch(database.db)
rateLimiter = Limiter(key_func=util.get_remote_address, storage_uri="memory://")


