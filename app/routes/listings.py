from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any


router = APIRouter(prefix="/listings", tags=["listings"])


@router.get("/", response_model=List[Dict[str, Any]])
async def getListings():
    return [{"title": "Product 1"}, {"title": "Product 2"}]


@router.post("/")
async def createListing():
    return {"message": "Listing created"}


@router.get("/{listingID}", response_model=Dict[str, Any])
async def getListing(listingID: str):
    return {"title": "Product 1"}


@router.put("/{listingID}")
async def updateListing(listingID: str):
    return {"message": "Listing updated"}