from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any
from typing_extensions import Annotated, Union, Optional

from ..database.database import getDBSession
from ..models.listings import Listing
from ..models.listings import Response as ListingResponses
from ..models.users import User, PrivilegedUser
from ..functions.auth import userRequired
import app.functions.data as data

import app.instances as instances

import cachetools.func
import sqlite3

router = APIRouter(prefix="/listings", tags=["listings"])

# listing = Listing(id='0', title="Product 1", description="Product 1 Description", category="Category 1", basePrice=10,
#                   multipleSKUs=True, addedAt=10000000, views=100, rating=4.5,
#                   ownerUser=User(id='0', username="User 1", profileURL='http://meow.com',
#                                  profilePictureURL="http://profile.com",
#                                  bannerURL="http://banner.com", description="User 1 Description",
#                                  joinedAt=1000000000)
#                   )


@router.api_route("/", methods=['GET', 'HEAD', 'OPTIONS'], response_model=ListingResponses.Listings)
async def getListings(conn: sqlite3.Connection = Depends(getDBSession),
                      query: Optional[str] = None,
                      category: Optional[str] = None,
                      subCategory: Optional[str] = None,
                      sort: Optional[str] = None,
                      order: Optional[str] = 'desc',
                      limit: int = 10,
                      offset: int = 0,
                      ):

    if limit > 40:
        raise HTTPException(status_code=400, detail="Limit must be less than 40")

    total, listings = instances.listingsSearch.query(conn,
                                                     query=query, offset=offset, limit=limit, category=category,
                                                     sort=sort, order=order, subCategory=subCategory)

    return ListingResponses.Listings(meta={
        'total': total,
        'limit': limit,
        'offset': offset,
        'query': query,
        'category': category,
        'sort': sort,
        'order': order,
    },
        data=listings
    )


@router.post("/", response_model=ListingResponses.Listing)
async def createListing(listing: Listing,
                        conn: sqlite3.Connection = Depends(getDBSession)):
    if not listing:
        raise HTTPException(status_code=400, detail="Invalid listing")

    return ListingResponses.Listing(meta={"id": "0"}, data=listing)


@router.get("/{listingID}", response_model=ListingResponses.Listing)
async def getListing(
        listingID: str,
        conn: sqlite3.Connection = Depends(getDBSession)):

    listingObj = data.getListingByID(conn, listingID)

    return ListingResponses.Listing(meta={"id": listingID}, data=listingObj)


@router.put("/{listingID}")
async def updateListing(listingFields: Listing):
    return listingFields
