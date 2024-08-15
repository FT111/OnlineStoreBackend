import contextlib

from ..database.databaseQueries import Queries
from ..functions import data

import sqlite3
import cachetools.func
import threading
import time
import math
from collections import defaultdict
from abc import ABC, abstractmethod
from typing import Optional, List
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..models.listings import Listing


class Search(ABC):
    """
    An abstract class for search algorithms
    """
    @abstractmethod
    def query(self, conn: contextlib.contextmanager, query: str, offset: int, limit: int) -> list:
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

    def __init__(self, connFunction: callable):
        self.tableName = 'listings'

        self.lastTimestamp = 0
        self.k1 = 1.5
        self.b = 0.75

        self.documents = []
        self.documentCount = 0
        self.documentFrequencies = defaultdict(int)
        self.averageDocumentLength = 0
        self.corpusLength = 0

        self.termFrequencies = defaultdict(list)

        self.loadExecutor = ThreadPoolExecutor(max_workers=12)

        # Load the table
        threading.Thread(target=self.loadTable, args=(connFunction,)).start()

    def loadTable(self, conn: callable):
        """
        Incrementally loads the table. This function is called every minute.
        :param conn:
        :return:
        """

        # Incrementally loads BM25 data
        newListings = Queries.Listings.getListingsSince(conn, self.lastTimestamp)
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
                loadedListingFutures.append(self.loadExecutor.submit(self.processDocument, description, id, title, category))
                # self.processDocument(description, id, title, category)

            for future in loadedListingFutures:
                future.result()

            self.documentCount += len(newListings)
            self.averageDocumentLength = self.corpusLength / self.documentCount

            print(f"Loaded {self.tableName}")
            print("Doc Frequencies: ", self.documentFrequencies)
            print("Doc Count: ", self.documentCount)
            print("Avg Doc Length: ", self.averageDocumentLength)

            print("Term Frequencies: ", self.termFrequencies)
            print(type(self.termFrequencies[0]))

        # # Schedule the next load - Uncomment in prod
        # time.sleep(60)
        # self.loadTable(conn)

    def processDocument(self, description: str, id, title: str, category: str):
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

        self.termFrequencies[category].append((id, rowTermFrequencies))

    def queryDocuments(self, query: Optional[str] = None, category: Optional[str] = None) -> list:
        tokenisedQuery = None

        if query is not None:
            tokenisedQuery = self.tokeniseQuery(query)

        queryScores = defaultdict(float)
        # Calculate BM25 scores
        # Checks against every category of stored listing terms
        for searchCategory in self.termFrequencies:
            for id, termFrequencies in self.termFrequencies[searchCategory]:

                if category == searchCategory or category is None:
                    documentLength = sum(termFrequencies.values())

                    # If a query is provided, score the terms against the query
                    if query is not None:
                        # Score against each term in the query
                        for term in tokenisedQuery:
                            # Only score terms that are in the document
                            if term not in termFrequencies:
                                continue

                            termScore = self.scoreTerm(documentLength, term, termFrequencies)
                            queryScores[id] += termScore
                    # If no query is provided, score every listing equally
                    else:
                        queryScores[id] = 1

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
            sortedListings = sorted(listings, key=lambda listing: listing.basePrice if listing.basePrice is not None else 0,
                                    reverse=reverse)
        elif sort == 'rating':
            sortedListings = sorted(listings, key=lambda listing: listing.rating, reverse=reverse)
        elif sort == 'views':
            sortedListings = sorted(listings, key=lambda listing: listing.views, reverse=reverse)
        elif sort == 'trending':
            currentTime = int(time.time())
            sortedListings = sorted(listings, key=lambda listing: (currentTime-listing.addedAt)/listing.views if listing.views > 0 else 1, reverse=reverse)
        else:
            sortedListings = listings

        return sortedListings

    @cachetools.func.ttl_cache(maxsize=128, ttl=300)
    def query(self, conn: contextlib.contextmanager, query: str, offset: int,
              limit: int, category: Optional[str] = None,
              sort: Optional[str] = None, order: Optional[str] = None) -> tuple[int, list]:

        """
        Searches the database using the BM25 algorithm
        :param conn: An context manager that returns a connection to a database
        :param query: A query to search for
        :param offset: How many results to skip, for pagination
        :param limit: How many results to return
        :param category: The category to search in. If None, searches all categories
        :param sort: The sort to use
        :param order: The order to use - asc or desc

        :return: A list of Listing objects
        """

        scores = self.queryDocuments(query, category)

        # Get the rows of the top results
        listings = data.idsToListings(conn, [id for id, _ in scores])

        listings = self.sortListings(listings, sort, order)

        topListings = listings[offset:offset + limit]

        return len(scores), topListings

