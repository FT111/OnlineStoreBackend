import sqlite3


def getTestDatabaseConnection():

	conn = sqlite3.connect('./app/database/databaseTest.db')
	conn.row_factory = sqlite3.Row

	try:
		yield conn
	finally:
		conn.close()


def getTestDBSession():
	with getTestDatabaseConnection() as conn:
		yield conn

