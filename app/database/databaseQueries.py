
from sqlite3 import Connection
from typing import Annotated


class Queries:
    """
    This class is responsible for executing SQL queries on the database.
    """

    @staticmethod
    def getRowsSince(conn: callable, tableName: str, timestamp: int):
        """
        Returns all rows since the timestamp.
        """

        print(type(conn))
        with conn() as connection:
            cursor = connection.cursor()

            cursor.execute(f"SELECT * FROM {tableName} WHERE addedAt > {timestamp}")
            return cursor.fetchall()
