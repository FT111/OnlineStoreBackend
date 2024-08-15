import sqlite3
from sqlite3 import Connection
from typing_extensions import Annotated, Literal, TypedDict, Final, Optional, List


class Queries:
    """
    This class is responsible for executing SQL queries on the database.
    """

    class Listings:

        @staticmethod
        def getListingsSince(conn: callable, timestamp: int) -> List[sqlite3.Row]:
            """
            Returns all rows since the timestamp.
            """

            with conn() as connection:
                cursor = connection.cursor()

                cursor.execute(f"""SELECT Li.id, Li.title, Li.description,
                         (
                            SELECT sCa.title 
                             FROM subCategories sCa
                             WHERE sCa.id = Li.subCategoryID
                        ) AS subCategory,
                        (
                             SELECT Ca.title
                             FROM categories Ca
                             WHERE Ca.id = (
                                 SELECT sCa.categoryID
                                 FROM subCategories sCa
                                 WHERE sCa.id = Li.subCategoryID
                             )
                        ) AS category
                     FROM listings Li
                     WHERE addedAt > ?""",
                               (timestamp,))

                return cursor.fetchall()

        @staticmethod
        def getListingsByIDs(conn: callable, listingIDs: list) -> list:
            """
            Get a listing by its ID
            """
            query = """
            SELECT
                   Li.id, Li.title, Li.description, Li.addedAt, Li.rating, Li.views,
    
                   (
                        SELECT Ca.title
                        FROM categories Ca
                        WHERE Ca.id = (
                            SELECT sCa.categoryID
                            FROM subCategories sCa
                            WHERE sCa.id = Li.subCategoryID
                        )
                   ) AS category,
                    (
                       SELECT sCa.title
                        FROM subCategories sCa
                        WHERE sCa.id = Li.subCategoryID
                   ) AS subCategory,
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
                        SELECT CASE
                            WHEN count(*) > 1 THEN 1
                            ELSE 0
                        END
                        FROM skus Sk
                        WHERE Sk.listingID = Li.id
                    ) AS multipleSKUs,
    
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

    class Categories:

        @staticmethod
        def getCategory(conn: callable, title) -> sqlite3.Row:
            """
            Returns a single category specified by a title
            :param title:
            :param conn:
            :return:
            """

            with conn as connection:
                cursor = connection.cursor()

                cursor.execute(f"""SELECT id, title, description,
                                    (
                                    SELECT json_group_array(
                                        json_object(
                                            'id', sCa.id,
                                            'title', sCa.title
                                        ) )
                                    FROM subCategories sCa
                                    WHERE sCa.categoryID = categories.id
                                    ) AS subCategories
                                    
                         FROM categories
                         WHERE title = ?""", (title,))

                return cursor.fetchone()

        @staticmethod
        def getAllCategories(conn: callable) -> List[sqlite3.Row]:
            """
            Returns all categories.
            """

            with conn as connection:
                cursor = connection.cursor()

                cursor.execute(f"""SELECT id, title, description,
                                    (
                                    SELECT json_group_array(
                                        json_object(
                                            'id', sCa.id,
                                            'title', sCa.title
                                        ) )
                                    FROM subCategories sCa
                                    WHERE sCa.categoryID = categories.id
                                    ) AS subCategories
                                    
                         FROM categories""")

                return cursor.fetchall()



