
import sqlite3


# Function to get the database connection - A dependency for DB operations
def getDBSession() -> sqlite3.Connection:
    conn = sqlite3.connect('databaseProd.db')
    conn.row_factory = sqlite3.Row
    return conn

getDBSession()