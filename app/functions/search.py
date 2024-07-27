
import sqlite3
import cachetools.func


class Search:
    """
        This class is responsible for searching the SQL database using the BM25 algorithm.

        Incrementally indexes new additions to the database every 5 minutes.
    """

    def __init__(self, tableName: str, columnName: str):
        self.tableName = tableName
        self.columnName = columnName

    def indexTable(self, conn: sqlite3.Connection):
        pass

    # Searches using BM25
    @cachetools.func.ttl_cache(maxsize=128, ttl=300)
    def searchTable(self, conn: sqlite3.Connection, query: str, offset: int, limit: int) -> list:
        pass

    # Tokenises the query, ready for a MB25 search
    @staticmethod
    def tokeniseQuery(query: str) -> list:
        tokenisedQuery = (query.lower()).split(" ")

        return tokenisedQuery
