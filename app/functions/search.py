import contextlib

from ..database.databaseQueries import Queries

import sqlite3
import cachetools.func
import threading
import time
import math
from collections import defaultdict


class Search:
    """
        This class is responsible for searching the SQL database using the BM25 algorithm.

        Incrementally indexes new additions to the database every minute.
    """

    def __init__(self, tableName: str, columnName: str, connFunction: callable):
        self.tableName = tableName

        self.lastTimestamp = 0
        self.k1 = 1.5
        self.b = 0.75

        self.documents = []
        self.documentCount = 0
        self.documentFrequencies = defaultdict(int)
        self.averageDocumentLength = 0

        self.termFrequencies = []

        # Load the table
        threading.Thread(target=self.loadTable, args=(connFunction,)).start()

    def loadTable(self, conn: callable):
        """
        Incrementally loads the table. This function is called every minute.
        :param conn:
        :return:
        """

        # Incrementally loads BM25 data
        newRows = Queries.getRowsSince(conn, self.tableName, self.lastTimestamp)
        print([row['title'] for row in newRows])
        # Update the last timestamp to the current time, for the next load
        self.lastTimestamp = int(time.time())

        if newRows:
            for id, title, description, *_ in newRows:
                self.processDocument(description, id, title)

            self.documentCount += len(newRows)
            self.averageDocumentLength = sum([sum(termFrequencies.values()) for id, termFrequencies in self.termFrequencies]) / self.documentCount

        # Index the table every minute
        threading.Timer(60, self.loadTable, args=(conn,)).start()

    def processDocument(self, description: str, id, title: str):
        """
        Processes a document for BM25 search
        """
        # Tokenise the terms
        terms = [*self.tokeniseQuery(title), *self.tokeniseQuery(description)]
        rowTermFrequencies = defaultdict(int)

        for term in terms:
            rowTermFrequencies[term] += 1

        for term in rowTermFrequencies:
            self.documentFrequencies[term] += 1

        self.termFrequencies.append((id, rowTermFrequencies))

    def queryDocuments(self, query) -> list:
        tokenisedQuery = self.tokeniseQuery(query)

        queryScores = defaultdict(float)
        # Calculate BM25 scores
        for id, termFrequencies in self.termFrequencies:

            documentLength = sum(termFrequencies.values())
            for term in tokenisedQuery:
                if term in termFrequencies:

                    termScore = self.scoreTerm(documentLength, term, termFrequencies)

                    queryScores[id] += termScore

        return self.sortScores(queryScores)

    @staticmethod
    def sortScores(queryScores: dict) -> list:
        queryScoresSorted = sorted(queryScores.items(), key= lambda item: item[1], reverse=True)

        return queryScoresSorted

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
    def searchTable(self, conn: contextlib.contextmanager, query: str, offset: int, limit: int) -> list:
        scores = self.queryDocuments(query)

        # Get the IDs of the top results
        topResults = [id for id, score in scores[offset:offset + limit]]

        # Get the rows of the top results
        with conn as connection:
            cursor = connection.cursor()
            topRows = cursor.execute(
                f"SELECT * FROM {self.tableName} WHERE id IN ({','.join(['?'] * len(topResults))})",
                topResults).fetchall()

        return topRows

    # Tokenises the query, ready for a MB25 search
    @staticmethod
    def tokeniseQuery(query: str) -> list:
        tokenisedQuery = (query.lower()).split(" ")

        return tokenisedQuery
