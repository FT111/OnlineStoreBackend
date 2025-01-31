import sqlite3
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from queue import Queue

from typing_extensions import Union, Optional


class DatabaseAdapter(ABC):
	"""
	Abstract class for database adapters
	Use this to adapt the system to use a different database
	"""

	@abstractmethod
	def execute(self, query: str, args: tuple = None) -> Union[list, int]:
		pass

	@abstractmethod
	def executemany(self, query: str, args: list = None) -> Union[list, int]:
		pass

	@abstractmethod
	def close(self):
		pass


@dataclass
class QueryTask:
	query: str
	args: Union[tuple, list]
	resultQueue: Queue
	isMany: bool = False


class SQLiteAdapter(DatabaseAdapter):
	"""
	Queued SQLite database handler
	Uses a single thread and connection to avoid SQlite's awful threading issues
	"""

	def __init__(self, path: str) -> None:
		localThread = threading.local()
		sqlite3.threadsafety = 1

		self.queryQueue = Queue()
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
				task = self.queryQueue.get()

				# Stop running if stopped
				if task is None:
					break

				try:
					# Execute the query
					cursor = self.connection.cursor()
					if task.args:
						# Execute the query with arguments
						if task.isMany:
							cursor.executemany(task.query, task.args)
						else:
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
				self.queryQueue.task_done()

	def execute(self, query: str, args: Optional[Union[tuple, list]] = None) -> Union[list, int]:
		"""
		Execute a query on the database
		:param query: An SQLite query
		:param args: Arguments for the query
		:return: Either the resulting rows of the query, affected row count or an SQLite3 database error
		"""

		# Result queue is used to return the result of the query by the handler
		# Awaited by the caller after the query is added to the query queue
		resultQueue = Queue()
		task = QueryTask(query, args, resultQueue)
		return self.putQueryTaskAndAwaitResult(task)

	def executemany(self, query: str, args: list = list) -> Union[list, int]:
		"""
		Executes multiple queries in a single transaction
		:param query: An SQLite query
		:param args: Arguments for the query
		:return: Either the resulting rows of the query, row count or an SQLite3 database error
		"""
		resultQueue = Queue()
		task = QueryTask(query, args, resultQueue, isMany=True)
		return self.putQueryTaskAndAwaitResult(task)

	def putQueryTaskAndAwaitResult(self, task: QueryTask):
		self.queryQueue.put(task)
		status, data = task.resultQueue.get()
		if status == 'error':
			raise data
		return data

	def close(self):
		self.running = False  # Stop new queries
		self.queryQueue.put(None)  # Signal thread to stop
		self.queryQueue.join()  # Wait for thread to stop
		if self.connection:
			self.connection.close()


db = SQLiteAdapter('./app/database/databaseDev.db')


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
	return db
