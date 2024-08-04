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

        # Load the table
        threading.Thread(target=self.loadTable, args=(connFunction,)).start()

    def loadTable(self, conn: callable):
        """
        Incrementally loads the table. This function is called every minute.
        :param conn:
        :return:
        """

        # Incrementally loads BM25 data
        newListings = Queries.getListingsSince(conn, self.lastTimestamp)
        # Update the last timestamp to the current time, for the next load
        self.lastTimestamp = int(time.time())

        if newListings:
            print([dict(row) for row in newListings])

            for id, title, description, category, *_ in newListings:

                ###############################################################
                for categoryList in self.termFrequencies.values():
                    print('categoryList:', categoryList)
                    if id in [id for id, *_ in categoryList]:  # Remove in prod
                        continue
                ###############################################################

                self.processDocument(description, id, title, category)

            print('term freqs:', self.termFrequencies)

            self.documentCount += len(newListings)
            self.averageDocumentLength = self.corpusLength / self.documentCount

            print(f"Loaded {self.tableName}")
            print("Doc Frequencies: ", self.documentFrequencies)
            print("Doc Count: ", self.documentCount)
            print("Avg Doc Length: ", self.averageDocumentLength)

            print("Term Frequencies: ", self.termFrequencies)
            print(type(self.termFrequencies[0]))

        # Index the table every minute
        threading.Timer(60, self.loadTable, args=(conn,)).start()

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
        for searchCategory in self.termFrequencies:
            for id, termFrequencies in self.termFrequencies[searchCategory]:

                if category == searchCategory or category is None:
                    documentLength = sum(termFrequencies.values())
                    if query is not None:
                        for term in tokenisedQuery:
                            if term in termFrequencies:
                                termScore = self.scoreTerm(documentLength, term, termFrequencies)
                                queryScores[id] += termScore
                    else:
                        queryScores[id] = 1

        print('queryScores:', queryScores)

        return self.sortScores(queryScores)

    def scoreTerm(self, documentLength, term, termFrequencies) -> float:
        """
        Scores a term using BM25 inverse document frequency
        """
        inverseDocumentFrequency = math.log(
            (self.documentCount - self.documentFrequencies[term] + 0.5) / (self.documentFrequencies[term] + 0.5))

        termScore = inverseDocumentFrequency * (termFrequencies[term] * (self.k1 + 1)) / (
                termFrequencies[term] + self.k1 * (1 - self.b + self.b * documentLength / self.documentCount))

        return termScore

    # Searches using BM25
    @cachetools.func.ttl_cache(maxsize=128, ttl=300)
    def query(self, conn: contextlib.contextmanager, query: str, offset: int,
              limit: int, category: Optional[str] = None) -> list:

        scores = self.queryDocuments(query, category)

        print(scores)

        # Get the IDs of the top results
        topResults = [id for id, score in scores[offset:offset + limit]]

        print('topResults:', topResults)

        # Get the rows of the top results
        listings = data.idsToListings(conn, topResults)

        print('listings:', listings)

        return listings

