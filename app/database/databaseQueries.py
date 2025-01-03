import json
import sqlite3

from typing_extensions import List

from app.models.listings import Listing, SKUWithStock

listingBaseQuery = """
SELECT
    Li.id, Li.title, Li.description, Li.addedAt, Li.rating, Li.views, Li.public,
    Ca.title AS category,
    sCa.title AS subCategory,
    json_object(
        'id', Us.id,
        'username', Us.username,
        'profileURL', '/users/' || Us.id,
        'profilePictureURL', Us.profilePictureURL,
        'bannerURL', Us.bannerURL,
        'description', Us.description,
        'joinedAt', Us.joinedAt
    ) AS ownerUser,
    (
        SELECT json_group_array(
            json_object(
                'id', Sk.id,
                'title', Sk.title,
                'price', Sk.price,
                'discount', Sk.discount,
                'stock', Sk.stock,
                'images', (
                    SELECT json_group_array(skIm.id)
                    FROM skuImages skIm
                    WHERE skIm.skuID = Sk.id
                ),
                'options', (
                    SELECT json_group_object(
                        (SELECT title FROM skuTypes WHERE id = SkVa.skuTypeID), SkVa.title
                    )
                    FROM skuValues SkVa
                    WHERE SkVa.id IN ( SELECT valueID FROM skuOptions WHERE skuID = Sk.id)
                )
            )
        )
        FROM skus Sk
        WHERE Sk.listingID = Li.id

    ) AS skus,
    
    (
        SELECT json_group_array(
            skIm.id
        )
        FROM skuImages skIm
        WHERE skIm.skuID IN (
            SELECT Sk.id
            FROM skus Sk
            WHERE Sk.listingID = Li.id
            ORDER BY Sk.price
        )
    ) AS images,
    
    (SELECT json_group_object(
        skTy.title, (
            SELECT DISTINCT json_group_array(
                SkVa.title
            )
            FROM skuValues SkVa
            WHERE SkVa.skuTypeID = skTy.id
        )
    )
    FROM skuTypes skTy
    WHERE skTy.listingID = Li.id
    ) AS skuOptions,
    
    min(Sk.price * (1 - Sk.discount / 100.0)) AS basePrice,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM skus Sk
            WHERE Sk.listingID = Li.id AND Sk.discount > 0
        ) THEN 1
        ELSE 0
    END AS hasDiscount,
    CASE
        WHEN count(Sk.id) > 1 THEN 1
        ELSE 0
    END AS multipleSKUs,
    count(Ev.id) AS views
FROM listings Li
LEFT JOIN subCategories sCa ON sCa.id = Li.subCategoryID
LEFT JOIN categories Ca ON Ca.id = sCa.categoryID
LEFT JOIN users Us ON Us.id = Li.ownerID
LEFT JOIN skus Sk ON Sk.listingID = Li.id
LEFT JOIN skuImages SkIm ON SkIm.skuID = (SELECT Sk.id FROM skus Sk WHERE Sk.listingID = Li.id LIMIT 1)
LEFT JOIN listingEvents Ev ON Ev.listingID = Li.id AND Ev.eventType = 'view'
{}
GROUP BY Li.id, Ca.title, sCa.title, Us.id
            """


class Queries:
    """
    This class is responsible for executing SQL queries on the database.
    """
    class Users:
        @staticmethod
        def getUserByEmail(cursor: callable, email: str) -> sqlite3.Row:
            """
            Get a user by their email
            """
            
            result = cursor.execute("SELECT * FROM users WHERE emailAddress = ?", (email,))
            user = result[0]
            return user

        @staticmethod
        def getUserByID(cursor: callable, userID: str) -> sqlite3.Row:
            """
            Get a user by their ID
            """
            query = """
                SELECT id, username, emailAddress, firstName, surname, 
                profilePictureURL, bannerURL, description, joinedAt,
                    (
                        SELECT json_group_array(
                               Li.id
                                )
                                FROM listings Li
                                WHERE Li.ownerID = Us.id
                    ) AS listingIDs
                
                FROM users Us
                WHERE id = ?"""
            
            result = cursor.execute(query, (userID,))
            user = result[0]

            return user

        @staticmethod
        def addUser(cursor: callable, user: dict):
            """
            Adds a user to the database
            :param cursor:
            :param user:
            :return:
            """

            
            cursor.execute("""
            INSERT INTO users (id, emailAddress, username, firstName, surname, passwordHash, passwordSalt, joinedAt)
            VALUES (?,?,?,?,?,?,?,?)
            """, (user['id'], user['email'], user['username'], user['firstName'], user['surname'], user['passwordHash'],
                           user['passwordSalt'], user['joinedAt'],))
            cursor.commit()

        @staticmethod
        def getPrivilegedUserByID(cursor: callable, userID: str) -> sqlite3.Row:
            """
            Get a privileged user by their ID
            """
            
            result = cursor.execute("SELECT * FROM users WHERE id = ?", (userID,))
            user = result[0]
            return user

    class Listings:
        @staticmethod
        def addListing(cursor, listing: Listing):
            """
            Add a listing to the database

            :param cursor:
            :param listing:
            :return:
            """
            
            result = cursor.execute("""
            INSERT INTO listings (id, title, description, ownerID, public, addedAt, views, rating, subCategoryID)
            VALUES (?,?,?,?,?,?,?,?,(SELECT id FROM subCategories Su WHERE Su.title==?))
            """, (listing.id, listing.title, listing.description, listing.ownerUser.id, listing.public,
                  listing.addedAt, 0, 0, listing.subCategory,))
            cursor.commit()

        @staticmethod
        def updateListing(cursor: callable, listing: Listing):
            """
            Update a listing in the database
            """
            
            cursor.execute("""
            UPDATE listings
            SET title = ?, description = ?, public = ?, 
            subCategoryID = (SELECT id FROM subCategories WHERE title = ?)
            WHERE id = ?
            """, (listing.title, listing.description, listing.public, listing.subCategory, listing.id))
            cursor.commit()

        @staticmethod
        def updateSKU(cursor: callable, sku: SKUWithStock):
            """
            Update a SKU in the database
            """
            
            result = cursor.execute("""
            UPDATE skus
            SET title = ?, price = ?, discount = ?, stock = ?
            WHERE id = ?
        
            """, (sku.title, sku.price, sku.discount, sku.stock, sku.id))

            for image in sku.images:
                cursor.execute("""
                INSERT OR REPLACE INTO skuImages (id, skuID)
                VALUES (?, ?)
                """, (image, sku.id))

            # Remove all options
            result = cursor.execute("DELETE FROM skuOptions WHERE skuID = ?", (sku.id,))
            # Add new options
            if sku.options:
                options = [(sku.id, value) for value in sku.options.values()]
                cursor.executemany("""
                INSERT OR REPLACE INTO skuOptions (skuID, valueID)
                VALUES (?, (SELECT id FROM skuValues WHERE title = ?))
                """, options)

            #     Add the updated SKU to the database
            cursor.commit()

        @staticmethod
        def addSKU(cursor: callable, sku: SKUWithStock, listingID: str):
            """
            Add a SKU to the database
            """
            
            result = cursor.execute("""
            INSERT INTO skus (id, listingID, title, price, discount, stock)
            VALUES (?,?,?,?,?,?)
            """, (sku.id, listingID, sku.title, sku.price, sku.discount, sku.stock))

            for image in sku.images:
                cursor.execute("""
                INSERT INTO skuImages (id, skuID)
                VALUES (?, ?)
                """, (image, sku.id))

            if sku.options:
                options = [(sku.id, value) for value in sku.options.values()]
                cursor.executemany("""
                INSERT INTO skuOptions (skuID, valueID)
                VALUES (?, (SELECT id FROM skuValues WHERE title = ?))
                """, options)

            cursor.commit()

        @staticmethod
        def getListingIDsByUsername(cursor: callable, username: str) -> List[int]:
            """
            Get a list of listing IDs by a username
            """
            
            result = cursor.execute("SELECT id FROM listings WHERE ownerID ="
                           " (SELECT Us.id FROM Users Us WHERE Us.username == ?)", (username,))
            listings = result
            return listings

        @staticmethod
        def getListingsSince(cursor: callable, timestamp: int) -> List[sqlite3.Row]:
            """
            Returns all rows since the timestamp.
            """

            result = cursor.execute(f"""SELECT Li.id, Li.title, Li.description,
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

            return result

        @staticmethod
        def getListingsByIDs(cursor: callable, listingIDs: list) -> list:
            """
            Get a listing by its ID
            """
            query = listingBaseQuery.format("""
            WHERE Li.id IN ({}) AND
            Li.public = 1
            """.format(','.join('?' * len(listingIDs))))


            result = cursor.execute(query, listingIDs)
            listing = result
            return listing

        @staticmethod
        def getListingByID(cursor: callable, listingID: str,
                           includePrivileged: bool = False,
                           requestUserID=None) -> sqlite3.Row:
            """
            Get a listing by its ID, with associated SKUs
            """
            query = listingBaseQuery.format(f"""
            WHERE Li.id = ?
            AND {'Li.ownerID = ?' if includePrivileged else 'Li.public = 1'}
            """)


            # Allow listing owners to view their own private listings
            if includePrivileged:
                result = cursor.execute(query, (listingID, requestUserID))
            else:
                result = cursor.execute(query, (listingID,))
            listing = result[0]
            return listing

        @staticmethod
        def getListingsByUserID(cursor, userID,
                                includePrivileged=False):

            query = listingBaseQuery.format(f"""
            WHERE Li.ownerID = ?
            """ + ("" if includePrivileged else "AND Li.public = 1"))


            result = cursor.execute(query, (userID,))
            listing = result
            return listing

        @staticmethod
        def getSKUByOptions(cursor: callable, options: dict, listingID: str) -> sqlite3.Row:
            """
            Get a SKU by its options
            """


            jsonOptions = json.dumps(options)
            query = """
            SELECT Sk.id
            FROM skuOptionsView Sk
            WHERE Sk.listingID = ?
            AND Sk.options = json(?)   
            """
            result = cursor.execute(query, (listingID, jsonOptions, ))
            sku = result[0]
            return sku

    class Categories:
        @staticmethod
        def getCategory(cursor: callable, title) -> sqlite3.Row:
            """
            Returns a single category specified by a title
            :param cursor:
            :param title:
            :return:
            """



            result = cursor.execute(f"""SELECT id, title, description, colour,
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

            return result[0]

        @staticmethod
        def getAllCategories(cursor: callable) -> List[sqlite3.Row]:
            """
            Returns all categories.
            """



            result = cursor.execute(f"""SELECT id, title, description, colour,
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

            return result

        @staticmethod
        def getCategoryBySubcategoryTitle(cursor: callable, subcategory: str) -> sqlite3.Row:
            """
            Get the category of a subcategory
            """
            
            result = cursor.execute("""
            SELECT Ca.id, Ca.title, Ca.description, Ca.colour
            FROM categories Ca
            JOIN subCategories sCa ON sCa.categoryID = Ca.id
            WHERE sCa.title = ?
            """, (subcategory,))
            category = result[0]
            return category



