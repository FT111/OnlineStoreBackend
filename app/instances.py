
from app.functions.search import ListingSearch
from app.database.database import getDBSession


listingsSearch = ListingSearch(getDBSession)


