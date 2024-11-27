from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any
from typing_extensions import Annotated, Union, Optional

from ..database.database import getDBSession
from ..models.listings import Listing, BaseListing
from ..models.listings import Response as ListingResponses
from ..models.users import User, PrivilegedUser
from ..functions.auth import userRequired
import app.functions.data as data

import app.instances as instances

import cachetools.func
import sqlite3

router = APIRouter(prefix="/listings", tags=["listings"])


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
async def createListing(listing: BaseListing,
                        user: User = Depends(userRequired),
                        conn: sqlite3.Connection = Depends(getDBSession)):
    if not listing:
        raise HTTPException(status_code=400, detail="Invalid listing")

    listing = data.createListing(conn, listing, user)

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
