import sqlite3
import threading

localThread = threading.local()


def getDB(db_path='./app/database/databaseDev.db') -> sqlite3.Connection:
    """
    Yields a connection to the database and closes it after the request is done.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    return conn


async def getDBSession():

    session = getDB()
    try:
        yield session
    finally:
        session.close()
