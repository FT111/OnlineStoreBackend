from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from typing_extensions import Optional

from ..database.database import getDBSession
from ..models.listings import Listing, ListingSubmission, ListingWithSKUs, SKUWithStock, SKUSubmission
from ..models.listings import Response as ListingResponses
from ..models.users import User
from ..functions.auth import userRequired, userOptional, verifyListingOwnership
import app.functions.data as data

import app.instances as instances

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
        'query': query.title() if query else None,
        'category': category,
        'sort': sort,
        'order': order,
    },
        data=listings
    )


@router.post("/", response_model=ListingResponses.Listing)
async def createListing(listing: ListingSubmission,
                        user=Depends(userRequired),
                        conn: sqlite3.Connection = Depends(getDBSession)):
    """
    Create a new listing.
    Requires an authentication token in the header.
    :param listing:
    :param user:
    :param conn:
    :return:
    """

    # Get the user from the database
    user: User = data.getUserByID(getDBSession(), user['id'])

    # Create the listing
    listing: Listing = data.createListing(conn, listing, user)

    # Prepare the listing for the response
    listing: ListingWithSKUs = ListingWithSKUs(**dict(listing),
                                               skus=[])

    return ListingResponses.Listing(meta={"id": listing.id}, data=listing)


@router.get("/{listingID}", response_model=ListingResponses.Listing)
async def getListing(
        listingID: str,
        includePrivileged: bool = False,
        user: Optional[Dict] = Depends(userOptional),
        conn: sqlite3.Connection = Depends(getDBSession)):

    try:
        if includePrivileged and user:
            listingObj = data.getListingByID(conn, listingID, includePrivileged=True, user=user)
        else:
            listingObj = data.getListingByID(conn, listingID)
    except NameError:
        raise HTTPException(status_code=404, detail="Listing not found")

    return ListingResponses.Listing(meta={"id": listingID}, data=listingObj)


@router.put("/{listingID}")
async def updateListing(listing: ListingWithSKUs,
                        user=Depends(userRequired),
                        conn: sqlite3.Connection = Depends(getDBSession)):

    verifyListingOwnership(listing.id, user)
    if user['id'] != listing.ownerUser.id:
        raise HTTPException(status_code=403, detail="You do not have permission to edit this listing")

    data.updateListing(conn, listing)

    return ListingResponses.Listing(meta={"id": listing.id},
                                    data=listing)


@router.put("/{listingID}/{skuID}")
async def updateSKU(sku: SKUWithStock,
                    listingID: str,
                    user=Depends(userRequired),
                    conn: sqlite3.Connection = Depends(getDBSession)):

    # Check if the user owns the listing - 401s if not
    listing = verifyListingOwnership(listingID, user)
    # Check if the SKU exists in the listing
    if sku.id not in [sku.id for sku in listing.skus]:
        raise HTTPException(status_code=404, detail="SKU not found")

    data.updateSKU(conn, sku)

    return ListingResponses.SKU(meta={"id": sku.id},
                                data=sku)


@router.post("/{listingID}/sku")
async def createSKU(sku: SKUSubmission,
                    listingID: str,
                    user=Depends(userRequired),
                    conn: sqlite3.Connection = Depends(getDBSession)):

    verifyListingOwnership(listingID, user)

    createdSKU = data.createSKU(conn, sku, listingID)

    return ListingResponses.SKU(meta={"id": createdSKU.id},
                                data=createdSKU)
