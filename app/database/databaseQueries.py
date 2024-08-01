
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

        with conn() as connection:
            cursor = connection.cursor()

            cursor.execute(f"SELECT * FROM {tableName} WHERE addedAt > {timestamp}")
            return cursor.fetchall()

    @staticmethod
    def getListingsByIDs(conn: Connection, listingIDs: list) -> list:
        """
        Get a listing by its ID
        """
        query = """
        SELECT
               Li.id, Li.title, Li.description, Li.addedAt,
               
               (
                   SELECT Ca.title 
                    FROM categories Ca
                    WHERE Ca.id = Li.categoryID
               ) AS category,
               (
                   SELECT json_object(
                       'id', Us.id,
                       'username', Us.username,
                       'profileURL', '/users/' || Us.id,
                       'profilePictureURL', Us.profilePictureURL,
                       'bannerURL', Us.bannerURL,
                       'description', Us.description,
                       'joinedAt', Us.joinedAt
                   )
                   FROM users Us
                   WHERE Us.id = Li.ownerID
               ) AS ownerUser,
               (
                   SELECT json_group_array(
                       json_object(
                           'id', Sk.id,
                           'title', Sk.title,
                           'description', Sk.description,
                           'price', Sk.price
                       )
                   )
                   FROM skus Sk
                   WHERE Sk.listingID = Li.id
               ) AS skus,
               
               (
                   SELECT min(Sk.price)
                   FROM skus Sk
                   WHERE Sk.listingID = Li.id
               ) AS basePrice,
               
               (
                   SELECT count(*)
                   FROM listingEvents Ev
                   WHERE Ev.eventType = 'view' AND Ev.listingID = Li.id
               ) AS views
        FROM listings Li
        WHERE Li.id IN ({})
            """.format(','.join('?' * len(listingIDs)))

        with conn as connection:
            cursor = connection.cursor()
            cursor.execute(query, listingIDs)
            listing = cursor.fetchall()
            return listing
