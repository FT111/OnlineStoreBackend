import math
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

from typing_extensions import Optional, Union

from .data import DataRepository
from .utils import quickSort
from ..database.database import SQLiteAdapter
from ..database.databaseQueries import Queries
from ..models.listings import Listing


def timeFunction(f):
	@wraps(f)
	def wrap(*args, **kw):
		ts = time.time()
		result = f(*args, **kw)
		te = time.time()
		print('func:%r args:[%r, %r] took: %2.4f sec' % \
			  (f.__name__, args, kw, te - ts))
		return result

	return wrap


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
		queryScoresSorted = quickSort(list(queryScores.items()), key=lambda item: item[1])

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

		self.k1 = 1.5
		self.b = 0.75

		# Inverted hierarchical index, pairs terms with a list of the documents they appear in
		# Stored as term -> category -> subCategory -> [(listingID, termFrequency)]
		self.invertedTermDocIndex = defaultdict(
			lambda: defaultdict(
				lambda: defaultdict(list[str, int])
			))
		# Standard index for category -> subCategory -> [(listingID, termFrequency)]
		# Used when no term is specified
		self.categoryIndex = defaultdict(
				lambda: defaultdict(list[str, int])
			)
		# This should all realistically be in a database

		self.documents = []
		self.documentCount = 0
		self.documentFrequencies = defaultdict(int)
		self.averageDocumentLength = 0
		self.corpusLength = 0

		self.termFrequencies = defaultdict(dict)

		self.loadExecutor = ThreadPoolExecutor(max_workers=12)

		# Load the table
		threading.Thread(target=self.loadTable, args=(dbSessionFunction,)).start()

	def loadTable(self, session: SQLiteAdapter, lastTimestamp: int = 0):
		"""
		Incrementally loads the table. This function is called every minute.
		:param lastTimestamp: The last timestamp the table was loaded
		:param session:  A database session
		:return:
		"""

		while True:
			# Incrementally loads new data to index
			newListings = Queries.Listings.getListingsSince(session, lastTimestamp)
			# Update the last timestamp to the current time, for the next load

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

			# Sleep for 10 seconds before loading the table again to load new listings
			lastTimestamp = int(time.time())
			time.sleep(10)

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

		for term, freq in rowTermFrequencies.items():
			self.documentFrequencies[term] += 1
			self.invertedTermDocIndex[term][category][subCategory].append((id, freq))

		# Add the term frequencies to the termFrequencies dictionary
		if subCategory not in self.termFrequencies[category]:
			self.termFrequencies[category][subCategory] = []

		self.categoryIndex[category][subCategory].append(id)
		self.termFrequencies[category][subCategory].append((id, rowTermFrequencies))

	@timeFunction
	def queryDocuments(self, query: Optional[str] = None, category: Optional[str] = None,
					   subCategory: Optional[str] = None) -> list:
		tokenisedQuery = None

		if query is not None:
			tokenisedQuery = self.tokeniseQuery(query)

		queryScores = defaultdict(float)

		if not tokenisedQuery:
			# If no query is provided, return all listings in the categories requested
			listings = self.getIndexedListingsByFilters(category, subCategory, None)
			if not listings:
				return []
			for listingID, termFrequency in listings:
				queryScores[listingID] += 1

			return self.sortScores(queryScores)

		# Calculate BM25 scores if a query is provided
		# Checks against every category of stored listing terms
		def _processQueryTerm(term):
			if term not in self.invertedTermDocIndex:
				return

			# Track scores internally to avoid race conditions
			termScores = defaultdict(float)

			listingsWithTermGenerator = self.getIndexedListingsByFilters(category, subCategory, term)
			# Calculate the score for each listing
			for listingID, termFrequency in listingsWithTermGenerator:
				documentLength = len(self.termFrequencies[listingID])
				# Get the score for the term
				score = self.scoreTerm(documentLength, term, termFrequency)
				# Add the score to the query scores
				# queryScores[listingID] += score
				termScores[listingID] += score

			return termScores

		with ThreadPoolExecutor(max_workers=16) as executor:
			scores = executor.map(_processQueryTerm, tokenisedQuery)

		for scoresPerTerm in scores:
			for listingID, score in scoresPerTerm.items():
				queryScores[listingID] += score

		return self.sortScores(queryScores)

	def getIndexedListingsByFilters(self, category: str, subCategory: str, term: Union[str, None]):
		if category is not None:
			if subCategory is not None:
				# If a category and subcategory are specified, return all listings in that category and subcategory
				if term is None:
					# If no term is specified, return all listings in that category and subcategory
					for indexedTerm in self.invertedTermDocIndex.keys():
						# Yield from every stored term in the index
						yield from self.invertedTermDocIndex[indexedTerm][category][subCategory]
				else:
					# If a term is specified, return all listings in that specific term's category and subcategory
					yield from self.invertedTermDocIndex[term][category][subCategory]
			else:
				if term is None:
					# If only a category but no term or subcategory is specified, return all subcategories in that category
					# for every stored term
					for indexedTerm in self.invertedTermDocIndex.keys():
						for subCategory in self.invertedTermDocIndex[indexedTerm][category].values():
							yield from subCategory

				else:
					# If only a category and term are specified, return all subcategories in that category for that term
					yield from [listing for subCategory in self.invertedTermDocIndex[term][category].values() for listing in
								subCategory]
		else:
			if not term:
				# If no category or term is specified, return all listings in all categories and subcategories
				# This looks horrifically inefficient, but its not too bad
				yield from [
					listing for term in self.invertedTermDocIndex.values()
					for category in term.values()
					for subCategory in category.values() for listing
					in subCategory
				]
			else:
				# If no category is specified, return all categories and subcategories
				yield from [listing for category in self.invertedTermDocIndex[term].values() for subCategory in
							category.values() for listing in subCategory]

	def scoreTerm(self, documentLength: int, term: str, termFrequencies: int) -> float:
		"""
		Scores a term using BM25 inverse document frequency
		"""
		inverseDocumentFrequency = math.log(
			(self.documentCount - self.documentFrequencies[term] + 0.5) / (self.documentFrequencies[term] + 0.5))

		termScore = inverseDocumentFrequency * (termFrequencies * (self.k1 + 1)) / (
				termFrequencies + self.k1 * (1 - self.b + self.b * documentLength / self.documentCount))

		return termScore

	@staticmethod
	def sortListings(listings: list[Listing], sort: str, order: str = 'desc') -> list:
		"""
		Sorts listings by a given sort
		"""

		# Sorts listings by a given sort, ascending or descending
		reverse = order == 'desc'

		if sort:
			sort = sort.lower()

		if sort == 'price':
			sortedListings = quickSort(listings,
									   key=lambda listing: listing['basePrice'] if listing[
																					   'basePrice'] is not None else 0,
									   reverse=reverse)
		elif sort == 'rating':
			sortedListings = quickSort(listings, key=lambda listing: listing['rating'], reverse=reverse)
		elif sort == 'views':
			sortedListings = quickSort(listings, key=lambda listing: listing['views'], reverse=reverse)
		elif sort == 'trending':
			currentTime = int(time.time())
			# Sort by the time since the listing was added, divided by the number of views
			# This will give a higher score to listings that have been added recently and have a lot of views
			# Listing views are defaulted to 1 if there are no views to avoid division by zero
			sortedListings = quickSort(listings, key=lambda listing: (
																			 currentTime - listing['addedAt']) /
																	 listing['views'] if listing['views'] > 0 else 1,
									   reverse=reverse)
		else:
			sortedListings = listings

		return sortedListings

	# @cached(TTLCache(maxsize=1024, ttl=300))
	def query(self, conn: sqlite3.Connection,
			  data: DataRepository,
			  query: str, offset: int,
			  limit: int, category: Optional[str] = None,
			  sort: Optional[str] = None, order: Optional[str] = None,
			  subCategory: Optional[str] = None
			  ) -> tuple[int, list]:

		"""
		Searches the database using the BM25 algorithm
		This function is for high-level querying, handling pagination and sorting
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
