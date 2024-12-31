import sqlite3
import threading
from contextlib import contextmanager

localThread = threading.local()


@contextmanager
def getDB(db_path='./app/database/databaseDev.db') -> sqlite3.Connection:
    """
    Yields a connection to the database and closes it after the request is done.
    """
    if not hasattr(localThread, 'conn'):
        localThread.conn = sqlite3.connect(db_path, check_same_thread=False)
        localThread.conn.row_factory = sqlite3.Row

    try:
        yield localThread.conn
    finally:
        localThread.conn.close()
        del localThread.conn


def getDBSession(db_path='./app/database/databaseDev.db') -> sqlite3.Connection:
    """
    Returns a connection to the database.
    """
    with getDB(db_path) as conn:
        yield conn
