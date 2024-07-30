
import sqlite3
import cachetools.func
import threading
import time


class Search:
    """
        This class is responsible for searching the SQL database using the BM25 algorithm.

        Incrementally indexes new additions to the database every minute.
    """

    def __init__(self, tableName: str, columnName: str, connFunction: callable):
        self.tableName = tableName
        self.columnName = columnName

        self.lastTimestamp = 0
        self.documents = []
        self.documentLengths = []

        # Load the table
        threading.Thread(target=self.loadTable, args=(connFunction,)).start()

    def loadTable(self, conn: callable):
        conn = conn()
        cursor = conn.cursor()

        # Incrementally loads BM25 data
        cursor.execute(f"SELECT * FROM {self.tableName} WHERE timestamp > {self.lastTimestamp}")
        self.lastTimestamp = int(time.time())

        for row in cursor.fetchall():
            self.documents.append(row)
            self.documentLengths.append(len(row[self.columnName].split(" ")))

        # Index the table every minute
        threading.Timer(60, self.loadTable).start()

    # Searches using BM25
    @cachetools.func.ttl_cache(maxsize=128, ttl=300)
    def searchTable(self, conn: sqlite3.Connection, query: str, offset: int, limit: int) -> list:
        pass

    # Tokenises the query, ready for a MB25 search
    @staticmethod
    def tokeniseQuery(query: str) -> list:
        tokenisedQuery = (query.lower()).split(" ")

        return tokenisedQuery
