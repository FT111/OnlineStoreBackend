import sqlite3
from contextlib import contextmanager


@contextmanager
def getDBSession() -> sqlite3.Connection:
    """
    Yields a connection to the database and closes it after the request is done.
    """

    conn = sqlite3.connect('./app/database/databaseProd.db')
    conn.row_factory = sqlite3.Row

    try:
        yield conn
    finally:
        conn.close()

