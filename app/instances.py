"""
Stores shared instances of classes that are used throughout the system.
Isolates shared state.
"""

import os

from dotenv import load_dotenv
from slowapi import Limiter, util

from app.database import database
from app.functions.email import EmailService
from app.functions.search import ListingSearch

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

listingsSearch = ListingSearch(database.db)
rateLimiter = Limiter(key_func=util.get_remote_address, storage_uri="memory://")
emailService = EmailService(senderAddress=os.getenv('EMAIL_ADDRESS'),
							senderPassword=os.getenv('EMAIL_PASSWORD'),
							senderHost=os.getenv('EMAIL_HOST'),
							senderPort=int(os.getenv('EMAIL_PORT')))
