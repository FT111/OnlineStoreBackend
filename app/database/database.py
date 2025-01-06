import sqlite3
import threading
from dataclasses import dataclass
from queue import Queue

from typing_extensions import Union

localThread = threading.local()
sqlite3.threadsafety = 1


@dataclass
class QueryTask:
    query: str
    args: tuple
    resultQueue: Queue


class Database:
    """
    Queued SQLite database handler
    Uses a single thread and connection to avoid SQlite's awful threading issues
    """
    def __init__(self, path: str) -> None:
        self.query_queue = Queue()
        self.path = path
        self.connection = None
        self.running = True
        self.startHandler()

    def startHandler(self):
        threading.Thread(target=self._processQueue, daemon=True).start()

    def _initConnection(self):
        """
        Initialise the connection
        """
        self.connection.row_factory = sqlite3.Row
        tempCursor = self.connection.cursor()
        # tempCursor.execute("PRAGMA foreign_keys = ON")
        # tempCursor.execute("PRAGMA journal_mode = WAL")
        tempCursor.close()

    def _processQueue(self):
        """
        Processes and executes queries from the queue
        :return:
        """
        self.connection = sqlite3.connect(self.path)
        self._initConnection()

        while self.running:
            try:
                task = self.query_queue.get()

                # Stop running if stopped
                if task is None:
                    break

                try:
                    # Execute the query
                    cursor = self.connection.cursor()
                    if task.args:
                        cursor.execute(task.query, task.args)
                    else:
                        cursor.execute(task.query)

                    # Handle different query types
                    if task.query.strip().upper().startswith('SELECT'):
                        result = cursor.fetchall()
                    else:
                        self.connection.commit()
                        result = cursor.rowcount

                    # Returns the result to the caller
                    task.resultQueue.put(('result', result))

                except Exception as e:
                    # Returns the error to the caller
                    task.resultQueue.put(('error', e))

            except Exception as e:
                print(f"Queue error: {e}")
            finally:
                self.query_queue.task_done()

    def execute(self, query: str, args: tuple = ()) -> Union[list, int]:
        """
        Execute a query on the database
        :param query: An SQLite query
        :param args: Arguments for the query
        :return: Either the result of the query or a database error
        """
        result_queue = Queue()
        task = QueryTask(query, args, result_queue)
        self.query_queue.put(task)

        # Wait for and return result
        status, data = result_queue.get()
        if status == 'error':
            raise data
        return data

    def close(self):
        self.running = False # Stop new queries
        self.query_queue.put(None)  # Signal thread to stop
        self.query_queue.join() # Wait for thread to stop
        if self.connection:
            self.connection.close()


dbQueue = Database('./app/database/databaseDev.db')


def createDatabase(location: str = './app/database/databaseDev.db'):
    """
    Create a new database
    :param location: The path to the new database
    :return:
    """
    db = sqlite3.connect(location)
    cursor = db.cursor()
    with open('./app/database/schema.sql', 'r') as f:
        cursor.executescript(f.read())
    db.commit()
    db.close()


def getDBSession():
    return dbQueue
