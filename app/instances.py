
from app.functions.search import Search
from app.database.database import getDBSession


listingsSearch = Search("listings", "description", getDBSession)


