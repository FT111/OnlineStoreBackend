import sqlite3


# Function to get the database connection - A dependency for DB operations
# Yields the connection and will always close it after a request is done
def getDBSession() -> sqlite3.Connection:
    conn = sqlite3.connect('databaseProd.db')
    conn.row_factory = sqlite3.Row

    try:
        yield conn
    finally:
        conn.close()

