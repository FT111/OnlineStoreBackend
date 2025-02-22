import json
import sqlite3
from collections import defaultdict

from typing_extensions import List, Union, Optional

from app.database.database import SQLiteAdapter, DatabaseAdapter
from app.models.analytics import Events
from app.models.listings import Listing, SKUWithStock, ListingWithSKUs
from app.models.transactions import InternalOrder
from app.models.users import PwdResetRequest

listingBaseQuery = """
SELECT
    Li.id, Li.title, Li.description, Li.addedAt, Li.rating, Li.public,
    Ca.title AS category,
    sCa.title AS subCategory,
    Co.title AS condition,
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
    
	(SELECT sum(Sk.stock) FROM skus Sk WHERE Sk.listingID = Li.id) AS totalStock,
    
    CASE
        WHEN count(Sk.id) > 1 THEN 1
        ELSE 0
    END AS multipleSKUs,
    (SELECT count(Ev.id) FROM listingEvents Ev
    WHERE Ev.listingID = Li.id
    AND Ev.eventType = 'view')
    AS views,
    (SELECT count(Ev.id) FROM listingEvents Ev
    WHERE Ev.listingID = Li.id
    AND Ev.eventType = 'click')
    AS clicks
FROM listings Li
LEFT JOIN subCategories sCa ON sCa.id = Li.subCategoryID
LEFT JOIN categories Ca ON Ca.id = sCa.categoryID
LEFT JOIN users Us ON Us.id = Li.ownerID
LEFT JOIN skus Sk ON Sk.listingID = Li.id
LEFT JOIN skuImages SkIm ON SkIm.skuID = (SELECT Sk.id FROM skus Sk WHERE Sk.listingID = Li.id LIMIT 1)
LEFT JOIN conditions Co ON Co.id = Li.conditionID
{}
GROUP BY Li.id, Ca.title, sCa.title, Us.id
            """

orderQuery = """
SELECT Ord.id, Ord.status, Ord.addedAt, Ord.updatedAt, Ord.purchaseID,
json_group_array(
	json_object(
		'id', Sk.id,
		'title', Sk.title,
		'price', OS.price,
		'discount', Sk.discount,
		'stock', Sk.stock,
		'quantity', OS.quantity,
		'images', (
			SELECT json_group_array(skIm.id)
			FROM skuImages skIm
			WHERE skIm.skuID = Sk.id
		),
		'listing', json_object(
			'id', Li.id,
			'title', Li.title,
			'description', Li.description,
			'addedAt', Li.addedAt
		)
	)
) AS skus,
{selection}
FROM orders Ord
LEFT JOIN orderSkus OS ON Ord.id = OS.orderID
LEFT JOIN skus Sk ON OS.skuID = Sk.id
LEFT JOIN listings Li ON Sk.listingID = Li.id
LEFT JOIN users OwUs ON OwUs.id = Li.ownerID
LEFT JOIN users ReUs ON ReUs.id = Ord.userID
{condition}
GROUP BY Ord.id
"""


class Queries:
	"""
	This class is responsible for executing SQL queries on the database.
	"""

	class Users:
		@staticmethod
		def getUserByEmail(cursor: DatabaseAdapter, email: str) -> sqlite3.Row:
			"""
			Get a user by their email
			"""

			result = cursor.execute("SELECT * FROM users WHERE emailAddress = ?", (email,))
			user = result[0] if result else None
			return user

		@staticmethod
		def getUserByID(cursor: DatabaseAdapter, userID: str) -> sqlite3.Row:
			"""
			Get a user by their ID
			"""
			query = """
                SELECT id, username, emailAddress, firstName, surname, 
                profilePictureURL, bannerURL, description, joinedAt,
                addressLine1, addressLine2, city, country, postcode,
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
			user = result[0] if result else None

			return user

		@staticmethod
		def addUser(cursor: DatabaseAdapter, user: dict):
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

		@staticmethod
		def getPrivilegedUserByID(cursor: DatabaseAdapter, userID: str) -> sqlite3.Row:
			"""
			Get a privileged user by their ID
			"""

			result = cursor.execute("SELECT * FROM users WHERE id = ?", (userID,))
			user = result[0] if result else None
			return user

		@staticmethod
		def getUserStatistics(cursor: DatabaseAdapter, userID: str, start: str, end: str) -> list[sqlite3.Row]:
			"""
			Get user statistics from listingEvents
			"""
			result = cursor.execute("""
            SELECT eventType,
            json_group_array(json_object('date', date, 'count', count)) as events
            FROM listingEventsByDay
            WHERE ownerID = ?
            AND date BETWEEN ? AND ?
            GROUP BY eventType
            """, (userID, start, end))

			return result

		@staticmethod
		def createPasswordReset(conn, reset: PwdResetRequest):
			"""
			Create a password reset request
			"""

			result = conn.execute("""
            INSERT INTO passwordResetRequests (id, userID, addedAt)
            VALUES (?,?,?)
            """, (reset.hashedId, reset.user.id, reset.addedAt))

			return result

		@classmethod
		def getPasswordReset(cls, conn, hashedId):
			"""
			Get a password reset request by its hashed ID
			"""

			result = conn.execute("""
            SELECT id, userID, addedAt
            FROM passwordResetRequests
            WHERE id = ?
            """, (hashedId,))

			return result

		@staticmethod
		def updatePassword(conn, userID, passwordHash):
			"""
			Update a user's password
			"""

			result = conn.execute("""
            UPDATE users
            SET passwordHash = ?
            WHERE id = ?
            """, (passwordHash, userID))

			return result

		@staticmethod
		def deletePasswordReset(conn, hashedId):
			"""
			Delete a password reset request
			"""

			result = conn.execute("""
            DELETE FROM passwordResetRequests
            WHERE id = ?
            """, (hashedId,))

			return result

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

		@staticmethod
		def updateListing(cursor: DatabaseAdapter, listing: ListingWithSKUs):
			"""
			Update a listing in the database
			"""

			cursor.execute("""
            UPDATE listings
            SET title = ?, description = ?, public = ?, 
            subCategoryID = (SELECT id FROM subCategories WHERE title = ?)
            WHERE id = ?
            """, (listing.title, listing.description, listing.public, listing.subCategory, listing.id))

			if listing.skuOptions:
				existingSKUTypes = cursor.execute("SELECT title FROM skuTypes WHERE listingID = ?", (listing.id,))
				existingSKUValues = cursor.execute("SELECT skV.title, skT.title as typeTitle FROM skuValues skV"
												   " JOIN skuTypes skT ON skT.id = skuTypeID"
												   " WHERE skT.listingID = ?", (listing.id,))

				# Remove existing options if not being defined
				listingSkuOptionKeys = listing.skuOptions.keys()
				listingSkuOptionValues = listing.skuOptions.values()
				skuTypesToRemove = [skuType['title'] for skuType in existingSKUTypes
									if skuType['title'] not in listing.skuOptions.keys()]

				# Remove existing values if not being redefined.
				# Compares existing values with new values
				newSKUOptions = defaultdict(list, listing.skuOptions)
				skuValuesToRemove = [skuValue['title'] for skuValue in existingSKUValues
									 if skuValue['title'] not in newSKUOptions[skuValue['typeTitle']]]

				if skuTypesToRemove:
					skuTypesToRemove.append(listing.id)
					# Delete existing options if not being defined
					cursor.execute(f"""
                    DELETE FROM skuTypes WHERE title in ({','.join('?' * (len(skuTypesToRemove) - 1))})
                    AND listingID = ?
                    """, tuple(skuTypesToRemove))

				if skuValuesToRemove:
					# Delete existing values if not being defined
					cursor.execute(f"""
                    DELETE FROM skuValues WHERE title in ({','.join('?' * len(skuValuesToRemove))})
                    """, tuple(skuValuesToRemove))

				# Add new option types if not already existing
				addedSKUTypes = [(skuType, listing.id) for skuType in listing.skuOptions.keys() if
								 skuType not in map(lambda x: x['title'], existingSKUTypes)]

				if addedSKUTypes:
					cursor.executemany("""
                    INSERT INTO skuTypes (title, listingID)
                    VALUES (?, ?)
                    """, addedSKUTypes)

				# Add new option values if not already existing
				# Transform skuValues to (title, skuTypeTitle, listingID)
				addedSKUValues = [(value, skuType, listing.id) for skuType, values in listing.skuOptions.items()
								  for value in values if value not in map(lambda x: x['title'], existingSKUValues)]

				if addedSKUValues:
					cursor.executemany("""
                    INSERT INTO skuValues (title, skuTypeID)
                    VALUES (?, (SELECT id FROM skuTypes WHERE title = ? AND listingID = ?))
                    """, addedSKUValues)

				# # Find SKUs with invalid options
				# cursor.execute("""
				# DELETE FROM skuOptions
				# WHERE valueID NOT IN (SELECT id FROM skuValues)
				# AND skuID IN (SELECT id FROM skus WHERE listingID = ?)
				# """, (listing.id,))

		@staticmethod
		def updateSKU(cursor: DatabaseAdapter, sku: SKUWithStock):
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
				for optionTuple in options:
					cursor.execute("""
                    INSERT OR REPLACE INTO skuOptions (skuID, valueID)
                    VALUES (?, (SELECT id FROM skuValues WHERE title = ?))
                    """, (optionTuple[0], optionTuple[1],))

		@staticmethod
		def addSKU(cursor: DatabaseAdapter, sku: SKUWithStock, listingID: str):
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

		@staticmethod
		def getListingIDsByUsername(cursor: DatabaseAdapter, username: str) -> List[int]:
			"""
			Get a list of listing IDs by a username
			"""

			result = cursor.execute("SELECT id FROM listings WHERE ownerID ="
									" (SELECT Us.id FROM Users Us WHERE Us.username == ?)", (username,))
			listings = result
			return listings

		@staticmethod
		def getListingsSince(cursor: DatabaseAdapter, timestamp: int) -> List[sqlite3.Row]:
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
		def getListingsByIDs(cursor: DatabaseAdapter, listingIDs: list) -> list:
			"""
			Get a listing by its ID
			"""
			query = listingBaseQuery.format("""
            WHERE Li.id IN ({}) AND
            Li.public = 1 AND
            totalStock > 0
            """.format(','.join('?' * len(listingIDs))))

			result = cursor.execute(query, listingIDs)
			return result

		@staticmethod
		def getListingByID(cursor: SQLiteAdapter, listingID: str,
						   includePrivileged: bool = False,
						   requestUserID=None) -> Union[sqlite3.Row, None]:
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

			if not result:
				return None
			return result[0]

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
		def getListingsBySKUids(cursor: DatabaseAdapter, skuIDs: list) -> List[sqlite3.Row]:
			"""
			Get a list of listings by their SKU IDs
			"""

			query = listingBaseQuery.format("""
            WHERE Sk.id IN ({})
            """.format(','.join('?' * len(skuIDs))))

			result = cursor.execute(query, tuple(skuIDs, ))
			return result

		@staticmethod
		def getSKUByOptions(cursor: DatabaseAdapter, options: dict, listingID: str) -> Optional[sqlite3.Row]:
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
			result = cursor.execute(query, (listingID, jsonOptions,))
			if not result:
				return None
			return result[0]

		@classmethod
		def getAllConditions(cls, conn):
			"""
			Get all conditions
			"""

			result = conn.execute("SELECT title FROM conditions")
			return result

		@staticmethod
		def getSKUsByIDs(conn, skuIDs: list) -> List[sqlite3.Row]:

			query = """
			SELECT Sk.id, Sk.title, Sk.price, Sk.discount, Sk.stock,
			json_object(
				'id', Us.id,
				'username', Us.username,
				'description', Us.description,
				'joinedAt', Us.joinedAt
			) AS ownerUser,
			(
				SELECT json_group_array(skIm.id)
				FROM skuImages skIm
				WHERE skIm.skuID = Sk.id
			) AS images,
			(
				SELECT json_group_object(
					(SELECT title FROM skuTypes WHERE id = SkVa.skuTypeID), SkVa.title
				)
				FROM skuValues SkVa
				WHERE SkVa.id IN ( SELECT valueID FROM skuOptions WHERE skuID = Sk.id)
			) AS options
			FROM skus Sk
			LEFT JOIN listings Li ON Li.id = Sk.listingID
			LEFT JOIN users Us ON Us.id = Li.ownerID
			WHERE Sk.id IN ({})
			""".format(','.join('?' * len(skuIDs)))

			return conn.execute(query, tuple(skuIDs))

		@staticmethod
		def updateSKUStock(conn, id, stock):
			conn.execute("""
			UPDATE skus
			SET stock = ?
			WHERE id = ?
			""", (stock, id))

	class Transactions:
		@staticmethod
		def addCheckout(cursor: DatabaseAdapter, checkout):
			"""
			Add a transaction to the database
			"""

			pass

		@staticmethod
		def addOrder(conn, order: InternalOrder):
			"""
			Add an order to the database
			:param conn: A connection to the database
			:param order: The order to add
			:return:
			"""

			result = conn.execute("""
			INSERT INTO orders (id, status, userID, addedAt, updatedAt, purchaseID)
			VALUES (?,?,?,?,?,?)
			""", (order.id, order.status, order.recipient.id, order.addedAt, order.updatedAt, order.purchaseID,))

			conn.executemany("""
			INSERT INTO orderSkus (orderID, skuID, quantity, price)
			VALUES (?,?,?,?)
			""", [(order.id, sku.sku.id, sku.quantity, sku.value) for sku in order.skus])

			return result

		@staticmethod
		def getSaleOrdersByUserID(conn, id):
			"""
			Get all sale orders by a user
			:param conn:
			:param id:
			:return:
			"""

			return conn.execute(
				orderQuery.format(
					selection="""
					json_object(
						'id', ReUs.id,
						'username', ReUs.username,
						'firstName', ReUs.firstName,
						'surname', ReUs.surname,
						'description', ReUs.description,
						'addressLine1', ReUs.addressLine1,
						'addressLine2', ReUs.addressLine2,
						'city', ReUs.city,
						'country', ReUs.country,
						'postcode', ReUs.postcode,
						'emailAddress', ReUs.emailAddress,
						'joinedAt', ReUs.joinedAt
					) AS recipient
					""",
					condition="""
							WHERE Li.ownerID = ?
			"""), (id,))

		@staticmethod
		def getPurchaseOrdersByUserID(conn, id):
			"""
			Get all purchase orders by a user
			:param conn:
			:param id:
			:return:
			"""

			return conn.execute(
				orderQuery.format(
					selection="""
					json_object(
						'id', OwUs.id,
						'username', OwUs.username,
						'description', OwUs.description,
						'addedAt', OwUs.joinedAt
					) AS seller
					""",
					condition="""
							WHERE Ord.userID = ?
			"""), (id,))

		@staticmethod
		def getOrder(conn, orderID):

			order = conn.execute("""
			SELECT Ord.id, Ord.status, Ord.addedAt, Ord.updatedAt, Ord.purchaseID,
			json_group_array(
				json_object(
					'id', Sk.id,
					'title', Sk.title,
					'price', OS.price,
					'discount', Sk.discount,
					'stock', Sk.stock,
					'quantity', OS.quantity,
					'images', (
						SELECT json_group_array(skIm.id)
						FROM skuImages skIm
						WHERE skIm.skuID = Sk.id
					),
					'listing', json_object(
						'id', Li.id,
						'title', Li.title,
						'description', Li.description,
						'addedAt', Li.addedAt
					)
				)
			) AS skus,
			json_object(
				'id', Us.id,
				'username', Us.username,
				'description', Us.description,
				'joinedAt', Us.joinedAt
			) AS seller,
			json_object(
				'id', ReUS.id,
				'username', ReUS.username,
				'description', ReUS.description,
				'joinedAt', ReUS.joinedAt
			) AS recipient
			
			FROM orders Ord
			LEFT JOIN orderSkus OS ON Ord.id = OS.orderID
			LEFT JOIN skus Sk ON OS.skuID = Sk.id
			LEFT JOIN listings Li ON Sk.listingID = Li.id
			LEFT JOIN users Us ON Us.id = Li.ownerID
			LEFT JOIN users ReUS ON ReUS.id = Ord.userID
			WHERE Ord.id = ?
			GROUP BY Ord.id
			""", (orderID,))

			return order[0] if order else None

		@staticmethod
		def updateOrderStatus(conn, orderID, status):
			"""
			Update an order's status
			:param conn:
			:param orderID:
			:param status:
			:return:
			"""

			return conn.execute("""
			UPDATE orders
			SET status = ?
			WHERE id = ?
			""", (status, orderID))

	class Analytics:
		@staticmethod
		def registerEvent(conn: DatabaseAdapter, event: Events.Event):
			"""
			Add an event to a listing
			"""

			conn.execute("""
            INSERT OR IGNORE INTO listingEvents (id, listingID, eventType, userID, userIP, addedAt)
            VALUES (?,?,?,?,?,?)
            """, (event.id, event.listingID, str(event), event.userID, event.userIP, event.time))

		@staticmethod
		def registerEvents(conn: DatabaseAdapter, events: List[Events.Event]):
			"""
			Add multiple events to the database
			"""

			# Convert events to a list of tuples ready for a SQL query
			eventTuples = [(event.id, event.listingID, str(event), event.userID, event.userIP, event.time)
						   for event in events]
			conn.executemany("""
            INSERT OR IGNORE INTO listingEvents (id, listingID, eventType, userID,userIP, addedAt)
            VALUES (?,?,?,?,?,?)
            """, eventTuples)

	class Categories:
		@staticmethod
		def getCategory(cursor: DatabaseAdapter, title) -> sqlite3.Row:
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

			return result[0] if result else None

		@staticmethod
		def getAllCategories(cursor: DatabaseAdapter) -> List[sqlite3.Row]:
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
		def getCategoryBySubcategoryTitle(cursor: DatabaseAdapter, subcategory: str) -> sqlite3.Row:
			"""
			Get the category of a subcategory
			"""

			result = cursor.execute("""
            SELECT Ca.id, Ca.title, Ca.description, Ca.colour,
                (
                SELECT json_group_array(
                    json_object(
                        'id', sCa.id,
                        'title', sCa.title
                    ) )
                FROM subCategories sCa
                WHERE sCa.categoryID = Ca.id
                ) AS subCategories
            FROM categories Ca
            JOIN subCategories sCa ON sCa.categoryID = Ca.id
            WHERE sCa.title = ?
            """, (subcategory,))
			category = result[0] if result else None
			return category
