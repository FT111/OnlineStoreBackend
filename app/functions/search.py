import math
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from typing_extensions import Optional

from .data import DataRepository
from ..database.database import Database
from ..database.databaseQueries import Queries
from ..models.listings import Listing


class Search(ABC):
	"""
	An abstract class for search algorithms
	"""

	@abstractmethod
	def query(self, conn, data,
			  query: str, offset: int, limit: int) -> list:
		pass

	@staticmethod
	def tokeniseQuery(query: str) -> list:
		tokenisedQuery = (query.lower()).split(" ")

		return tokenisedQuery

	@abstractmethod
	def loadTable(self, conn: callable):
		pass

	@abstractmethod
	def queryDocuments(self, query, category) -> list:
		pass

	@abstractmethod
	def processDocument(self, *args):
		pass

	@staticmethod
	def sortScores(queryScores: dict) -> list:
		queryScoresSorted = sorted(queryScores.items(), key=lambda item: item[1], reverse=True)

		return queryScoresSorted

	@abstractmethod
	def scoreTerm(self, documentLength, term, termFrequencies) -> float:
		pass


# Implements the BM25 search algorithm for listings
class ListingSearch(Search):
	"""
		This class is responsible for searching the SQL database using the BM25 algorithm.

		Incrementally indexes new additions to the database every minute.
	"""

	def __init__(self, dbSessionFunction):
		self.tableName = 'listings'

		self.lastTimestamp = 0
		self.k1 = 1.5
		self.b = 0.75

		self.documents = []
		self.documentCount = 0
		self.documentFrequencies = defaultdict(int)
		self.averageDocumentLength = 0
		self.corpusLength = 0

		self.termFrequencies = defaultdict(dict)

		self.loadExecutor = ThreadPoolExecutor(max_workers=12)

		# Load the table
		threading.Thread(target=self.loadTable, args=(dbSessionFunction,)).start()

	def loadTable(self, session: Database):
		"""
		Incrementally loads the table. This function is called every minute.
		:param session:  A database session
		:return:
		"""
		# Incrementally loads BM25 data
		newListings = Queries.Listings.getListingsSince(session, self.lastTimestamp)
		# Update the last timestamp to the current time, for the next load
		self.lastTimestamp = int(time.time())

		if newListings:

			loadedListingFutures = []

			for id, title, description, subCategory, category, *_ in newListings:
				# ###############################################################
				# for categoryList in self.termFrequencies.values():
				#     print('categoryList:', categoryList)
				#     if id in [id for id, *_ in categoryList]:  # Remove in prod
				#         continue
				# ###############################################################

				# Process the document in a separate thread
				loadedListingFutures.append(
					self.loadExecutor.submit(self.processDocument, description, id, title, category, subCategory))
			# self.processDocument(description, id, title, category)

			for future in loadedListingFutures:
				future.result()

			self.documentCount += len(newListings)
			self.averageDocumentLength = self.corpusLength / self.documentCount

	# # Schedule the next load - Uncomment in prod
	# time.sleep(60)
	# self.loadTable(database.dbQueue)

	def processDocument(self, description: str, id, title: str, category: str, subCategory: str):
		"""
		Processes a document for BM25 search
		"""
		# Tokenise the terms
		terms = [*self.tokeniseQuery(title), *self.tokeniseQuery(description)]
		self.corpusLength += len(terms)
		rowTermFrequencies = defaultdict(int)

		for term in terms:
			rowTermFrequencies[term] += 1

		for term in rowTermFrequencies:
			self.documentFrequencies[term] += 1

		# Add the term frequencies to the termFrequencies dictionary
		if subCategory not in self.termFrequencies[category]:
			self.termFrequencies[category][subCategory] = []

		self.termFrequencies[category][subCategory].append((id, rowTermFrequencies))

	def queryDocuments(self, query: Optional[str] = None, category: Optional[str] = None,
					   subCategory: Optional[str] = None) -> list:
		tokenisedQuery = None

		if query is not None:
			tokenisedQuery = self.tokeniseQuery(query)

		queryScores = defaultdict(float)
		# Calculate BM25 scores
		# Checks against every category of stored listing terms
		for searchCategory in self.termFrequencies:
			for searchSubCategory in self.termFrequencies[searchCategory]:
				for id, termFrequencies in self.termFrequencies[searchCategory][searchSubCategory]:

					if category != searchCategory and category is not None:
						continue

					if subCategory != searchSubCategory and subCategory is not None:
						continue
					documentLength = sum(termFrequencies.values())

					# If a query is provided, score the terms against the query
					if query is None:
						# If no query is provided, score every listing equally
						queryScores[id] = 1
						continue
					# Score against each term in the query
					for term in tokenisedQuery:
						# Only score terms that are in the document
						if term not in termFrequencies:
							continue

						termScore = self.scoreTerm(documentLength, term, termFrequencies)
						queryScores[id] += termScore

		return self.sortScores(queryScores)

	def scoreTerm(self, documentLength: int, term: str, termFrequencies: dict) -> float:
		"""
		Scores a term using BM25 inverse document frequency
		"""
		inverseDocumentFrequency = math.log(
			(self.documentCount - self.documentFrequencies[term] + 0.5) / (self.documentFrequencies[term] + 0.5))

		termScore = inverseDocumentFrequency * (termFrequencies[term] * (self.k1 + 1)) / (
				termFrequencies[term] + self.k1 * (1 - self.b + self.b * documentLength / self.documentCount))

		return termScore

	@staticmethod
	def sortListings(listings: list[Listing], sort: str, order: str = 'desc') -> list:
		"""
		Sorts listings by a given sort
		"""

		reverse = order == 'desc'

		if sort:
			sort = sort.lower()

		if sort == 'price':
			sortedListings = sorted(listings,
									key=lambda listing: listing['basePrice'] if listing['basePrice'] is not None else 0,
									reverse=reverse)
		elif sort == 'rating':
			sortedListings = sorted(listings, key=lambda listing: listing['rating'], reverse=reverse)
		elif sort == 'views':
			sortedListings = sorted(listings, key=lambda listing: listing['views'], reverse=reverse)
		elif sort == 'trending':
			currentTime = int(time.time())
			sortedListings = sorted(listings, key=lambda listing: (
																		  currentTime - listing['addedAt']) / listing['views'] if listing['views'] > 0 else 1,
									reverse=reverse)
		else:
			sortedListings = listings

		return sortedListings

	# @cachetools.func.ttl_cache(maxsize=128, ttl=300)
	def query(self, conn: sqlite3.Connection,
			  data: DataRepository,
			  query: str, offset: int,
			  limit: int, category: Optional[str] = None,
			  sort: Optional[str] = None, order: Optional[str] = None,
			  subCategory: Optional[str] = None
			  ) -> tuple[int, list]:

		"""
		Searches the database using the BM25 algorithm
		:param data: A data repository object with an active database connection
		:param subCategory: The subcategory to search in
		:param conn: An context manager that returns a connection to a database
		:param query: A query to search for
		:param offset: How many results to skip, for pagination
		:param limit: How many results to return
		:param category: The category to search in. If None, searches all categories
		:param sort: The sort to use
		:param order: The order to use - asc or desc

		:return: A list of Listing objects
		"""

		scores = self.queryDocuments(query, category, subCategory)

		# Get the full listings from the listingID scores
		listings = data.idsToListings([score[0] for score in scores])
		# Get the rows of the top results
		listings = self.sortListings(listings, sort, order)
		# Paginate the results
		topListings = listings[offset:offset + limit]

		return len(listings), topListings
