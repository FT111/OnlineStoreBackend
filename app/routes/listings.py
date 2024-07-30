from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any
from typing_extensions import Annotated, Union, Optional

from ..database.database import getDBSession
from ..models.listings import Listing, ListingWithSales, SKU
from ..models.listings import Response as ListingResponses
from ..models.users import User, PrivilegedUser, DatabaseUser

import cachetools.func
import sqlite3

router = APIRouter(prefix="/listings", tags=["listings"])

listing = Listing(id='0', title="Product 1", description="Product 1 Description", category="Category 1", basePrice=10,
                  multipleSKUs=True, addedAt=10000000, views=100, rating=4.5,
                  ownerUser=User(id='0', username="User 1", profileURL='http://meow.com',
                                 profilePictureURL="http://profile.com",
                                 bannerURL="http://banner.com", description="User 1 Description",
                                 joinedAt=1000000000)
                  )


@router.get("/", response_model=ListingResponses.Listings)
async def getListings(conn: sqlite3.Connection = Depends(getDBSession),
                      query: Optional[str] = None,
                      category: Optional[str] = None,
                      limit: int = 10,
                      offset: int = 0):

    return ListingResponses.Listings(meta={
        'total': 0,
        'limit': limit,
        'offset': offset,
        'query': query,
        'category': category
    },
        data=[
            listing for i in range(50)
        ]
    )


@router.post("/")
async def createListing(listing: Listing,
                        conn: sqlite3.Connection = Depends(getDBSession)):
    if not listing:
        raise HTTPException(status_code=400, detail="Invalid listing")

    return ResponseModel("Listing created successfully", "success")


@router.get("/{listingID}", response_model=Dict[str, Any])
async def getListing(listingID: str):
    return {"title": "Product 1"}


@router.put("/{listingID}")
async def updateListing(listingID: str):
    return {"message": "Listing updated"}
