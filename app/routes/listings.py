from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from typing_extensions import Annotated, Union

from ..database.database import getDBSession
from ..models.listings import Listing, PrivilegedListing, ListingGroup
from ..models.users import User, PrivilegedUser, DatabaseUser


import sqlite3


router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("/", response_model=ListingGroup)
async def getListings(conn: sqlite3.Connection = Depends(getDBSession),
                      query=Union[str, None],
                      category=Union[str, None],
                      limit: int = 10,
                      offset: int = 0):

    return ListingGroup()


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