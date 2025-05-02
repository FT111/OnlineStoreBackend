import math
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

from cachetools import cached, TTLCache
from typing_extensions import Optional, Union
from typing_extensions import Tuple, Dict, List

from .data import DataRepository
from .utils import quickSort
from ..constants import SUFFIXES, PROCESSED_SUFFIXES, COMMON_TYPO_LETTERS
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
		return result, te - ts

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
	def tokeniseQuery(query: str, typoMitigation: bool = False) -> Tuple[Dict[str, int], Dict[str, Union[bool, str]]]:
		"""
		Tokenises a query into a list of terms
		Stems the terms, removing common suffixes
		If a term is hyphenated, it splits the term into its components
		If requested, it also adds additional terms with swapped letters for common typos
		:param query: The query to tokenise
		:param typoMitigation: Whether to add common typos to the tokenised query - Avoid when indexing to avoid bloat
		:return:
		"""
		tokenisedQuery = {}
		for term in query.lower().split(' '):
			# If the term is already in the tokenised query, skip it
			if tokenisedQuery.get(term, None):
				continue

			# Add the term to the tokenised query - 'False' means it an original word not added from a typo-check
			tokenisedQuery[term] = False
		originalQueryWordCount = len(tokenisedQuery)

		for term in list(tokenisedQuery):
			if term.split('-') != [term]:
				# If the term is hyphenated, split it into its components
				# Remove the hyphenated term from the tokenised query
				tokenisedQuery.pop(term)
				term = term.split('-')
				# Add the words to the tokenised query
				tokenisedQuery.update({word: False for word in term})
				# Add the number of sub-words in the hyphenated term to the original word count
				originalQueryWordCount += len(term) - 1
				continue

			if len(term) > 3:
				# If the term is longer than 3 characters, check for common suffixes and remove them
				for length in reversed(range(1, list(SUFFIXES.keys())[-1]+1)):
					# Check if the term ends with a suffix - Checks for the longest possible suffix option first,
					# then shorter ones in order
					if PROCESSED_SUFFIXES.get(term[-length:], None) is not None:
						# If has a suffix, remove it
						tokenisedQuery[term[:-length]] = term
						break
			# If this isn't a word already added from a typo-check, check for typos
			# Avoids an infinite loop and unnecessary words
			if not tokenisedQuery.get(term, True) and typoMitigation:
				# Check for common typos per letter - If so, add the adjusted word to the tokenised query
				for index, letter in enumerate(term):
					if COMMON_TYPO_LETTERS.get(letter, None) is not None:

						# Add possible variants of the word to the tokenised query
						# Have them point to the original word
						tokenisedQuery.update(
							{term[:index] + typoLetter + term[index + 1:]: term for typoLetter in COMMON_TYPO_LETTERS[letter]}
						)

		return {'originalWordCount': originalQueryWordCount}, tokenisedQuery

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
		queryScoresSorted = quickSort(list(queryScores.items()), key=lambda item: item[1], reverse=True)

		return queryScoresSorted

	@abstractmethod
	def scoreTerm(self, documentLength, term, termFrequencies) -> float:
		pass


# Implements the BM25 search algorithm for listings
class ListingSearch(Search):
	"""
		This class is responsible for searching the database using the BM25 algorithm.
		Incrementally indexes new additions to the database every minute.

		Uses a multi-threaded approach to process documents in parallel.
		 and stems words for better matching.
		 Search results are cached for 20 seconds to improve performance.
	"""

	def __init__(self, dbSessionFunction):
		self.tableName = 'listings'

		self.k1 = 1.5
		self.b = 0.75

		# Inverted hierarchical index, pairs terms with a list of the documents they appear in
		# Stored as term -> category -> subCategory -> [(listingID, termFrequency)]
		self.invertedTermDocIndex = defaultdict(
			lambda: defaultdict(
				lambda: defaultdict(list)
			))
		# Standard index for category -> subCategory -> [(listingID, termFrequency)]
		# Used when no term is specified
		self.categoryIndex = defaultdict(
				lambda: defaultdict(list)
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

			# Sleep for 5 seconds before loading the table again to load new listings
			lastTimestamp = int(time.time())
			time.sleep(5)

	def processDocument(self, description: str, id, title: str, category: str, subCategory: str):
		"""
		Processes a document for BM25 search
		"""
		# Tokenise the terms
		terms = [*list(self.tokeniseQuery(title)[1].keys()), *list(self.tokeniseQuery(description)[1].keys())]
		self.corpusLength += len(terms)
		rowTermFrequencies = defaultdict(int)

		for term in terms:
			rowTermFrequencies[term] += 1

		for term, freq in rowTermFrequencies.items():
			self.documentFrequencies[term] += 1
			self.invertedTermDocIndex[term][category][subCategory].append((id, freq))

		self.categoryIndex[category][subCategory].append(id)
		self.termFrequencies[id] = rowTermFrequencies

	@timeFunction
	def queryDocuments(self, query: Optional[str] = None, category: Optional[str] = None,
					   subCategory: Optional[str] = None) -> Tuple[dict, list]:
		tokenisedQuery = None
		typoWords = {}

		if query is not None:
			meta, tokenisedQuery = self.tokeniseQuery(query, typoMitigation=True)

			# Filters to only words added in the query for typo-mitigation - Non-typo words are set to False
			typoWords = {word: tokenisedQuery[word] for word in tokenisedQuery if tokenisedQuery[word]}
			tokenisedQuery = list(tokenisedQuery.keys())

		queryScores = defaultdict(float)

		if not tokenisedQuery:
			# If no query is provided, return all listings in the categories requested
			listings = self.getIndexedListingsByFilters(category, subCategory, None)
			if not listings:
				return {}, []
			for listingID, termFrequency in listings:
				queryScores[listingID] += 1

			return {}, self.sortScores(queryScores)

		# Calculate BM25 scores if a query is provided
		# Checks against every category of stored listing terms
		def _processQueryTerm(term):
			if term not in self.invertedTermDocIndex:
				return {}

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

		if len(tokenisedQuery) > 4:
			# If the query is a bit long, use multithreading to process the query in parallel
			with ThreadPoolExecutor(max_workers=16) as executor:
				# The query is split into its terms and each term is processed in parallel
				scores = executor.map(_processQueryTerm, tokenisedQuery)
		else:
			# If the query is short, process it in a single thread
			# Avoids the overhead of creating a thread pool, faster for small queries
			scores = [_processQueryTerm(term) for term in tokenisedQuery]

		for scoresPerTerm in scores:
			# For each term, add the scores to the overall listing scores
			for listingID, score in scoresPerTerm.items():
				queryScores[listingID] += score

		return self.returnWithSuggestedQueryIfApplicable(query, queryScores, tokenisedQuery, typoWords)

	def returnWithSuggestedQueryIfApplicable(self, query, queryScores, tokenisedQuery, typoWords):
		# Check if any typo-terms returned more results than the original query
		# If so, suggest it to the user
		for index, term in enumerate(tokenisedQuery):
			if not self.invertedTermDocIndex.get(term, None):
				continue
			# Check if the term is a typo
			if typoWords.get(term, False):
				if self.documentFrequencies.get(term, 0) > self.documentFrequencies.get(typoWords[term], 0):
					originalQueryWords = query.split(' ')
					replacementIndex = originalQueryWords.index(typoWords[term])
					return {
						'suggestedQuery': ' '.join(
							originalQueryWords[:replacementIndex] + [term] + originalQueryWords[replacementIndex + 1:]),
					}, self.sortScores(queryScores)
		return {}, self.sortScores(queryScores)

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
	def sortListings(listings: List[Listing], sort: str, order: str = 'desc') -> list:
		"""
		Sorts listings by a given sort
		"""

		# Sorts listings by a given sort, ascending or descending
		reverse = order == 'des'

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

	@cached(TTLCache(maxsize=1024, ttl=20))
	def query(self, conn: sqlite3.Connection,
			  data: DataRepository,
			  query: str, offset: int,
			  limit: int, category: Optional[str] = None,
			  sort: Optional[str] = None, order: Optional[str] = None,
			  subCategory: Optional[str] = None
			  ) -> Tuple[Dict[str, float], List[Listing]]:

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

		query, elapsedTime = self.queryDocuments(query, category, subCategory)
		meta, scores = query

		# Get the full listings from the listingID scores
		listings = data.idsToListings([score[0] for score in scores])
		# If no listings are found, return an empty list
		if not listings:
			return {'total': 0, 'elapsed': 0}, []

		preSortedListings = []
		# Presort the listings by their relevance score
		# This is done as idsToListings returns a completely unsorted list for some reason
		for listingId, score in scores:
			fullListing = [listing for listing in listings if listing['id'] == listingId]
			if len(fullListing) > 0:
				preSortedListings.append(fullListing[0])

		# Get the rows of the top results
		listings = self.sortListings(preSortedListings, sort, order)
		# Paginate the results
		topListings = listings[offset:offset + limit]

		# Return the meta data and the listings
		queryData = {'total': len(listings), 'elapsed': elapsedTime, 'suggestedQuery': meta.get('suggestedQuery', None)}
		return queryData, topListings

