from typing import Dict

from fastapi import APIRouter, Depends, HTTPException
from typing_extensions import Optional

import app.instances as instances
from app.functions.data import DataRepository
from ..database import database
from ..functions.auth import userRequired, userOptional, verifyListingOwnership
from ..models.categories import Category
from ..models.listings import Listing, ListingSubmission, ListingWithSKUs, SKUWithStock, SKUSubmission
from ..models.listings import Response as ListingResponses
from ..models.users import User

router = APIRouter(prefix="/listings", tags=["listings"])


@router.api_route("/", methods=['GET', 'HEAD', 'OPTIONS'], response_model=ListingResponses.Listings)
async def getListings(query: Optional[str] = None,
                      category: Optional[str] = None,
                      subCategory: Optional[str] = None,
                      sort: Optional[str] = None,
                      order: Optional[str] = 'desc',
                      limit: int = 10,
                      offset: int = 0
                      ):
    data = DataRepository(database.db)

    if limit > 40:
        raise HTTPException(status_code=400, detail="Limit must be less than 40")

    total, listings = instances.listingsSearch.query(database.db, data,
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
                        user=Depends(userRequired)):
    """
    Create a new listing.
    Requires an authentication token in the header.
    :param listing:
    :param user:
    :param database.dbQueue:
    :return:
    """

    data = DataRepository(database.db)

    # Get the user and category from the database
    user: User = data.getUserByID(user['id'])
    category: Optional[Category] = data.getCategoryBySubcategoryTitle(listing.subCategory)
    if not category: # Verifies that the category and relevant subcategory exists
        raise HTTPException(status_code=404, detail="Category not found")

    # Create the listing
    listing: Listing = data.createListing( listing, user)

    # Prepare the listing for the response
    listing: ListingWithSKUs = ListingWithSKUs(**dict(listing),
                                               skus=[])

    return ListingResponses.Listing(meta={"id": listing.id}, data=listing)


@router.get("/{listingID}", response_model=ListingResponses.Listing)
async def getListing(
        listingID: str,
        includePrivileged: bool = False,
        user: Optional[Dict] = Depends(userOptional)):
    """
    Get a listing by its ID.
    Users can request their own listings with privileged information (such as stock levels).
    :param listingID:
    :param includePrivileged:
    :param user:
    :param database.dbQueue:
    :return:
    """

    data = DataRepository(database.db)

    if includePrivileged and user:
        listingObj = data.getListingByID(listingID, includePrivileged=True, user=user)
    else:
        listingObj = data.getListingByID(listingID)

    return ListingResponses.Listing(meta={"id": listingID}, data=listingObj)


@router.put("/{listingID}")
async def updateListing(listing: ListingWithSKUs,
                        user=Depends(userRequired)):

    data = DataRepository(database.db)

    verifyListingOwnership(data, listing.id, user)
    if user['id'] != listing.ownerUser.id:
        raise HTTPException(status_code=403, detail="You do not have permission to edit this listing")

    data.updateListing(listing)

    return ListingResponses.Listing(meta={"id": listing.id},
                                    data=listing)


@router.put("/{listingID}/{skuID}")
async def updateSKU(sku: SKUWithStock,
                    listingID: str,
                    user=Depends(userRequired)):

    data = DataRepository(database.db)

    # Check if the user owns the listing - 401s if not
    listing = verifyListingOwnership(data, listingID, user)
    # Check if the SKU exists in the listing
    if sku.id not in [sku.id for sku in listing.skus]:
        raise HTTPException(status_code=404, detail="SKU not found")

    data.updateSKU(sku, listing.id)

    return ListingResponses.SKU(meta={"id": sku.id},
                                data=sku)


@router.post("/{listingID}/sku")
async def createSKU(sku: SKUSubmission,
                    listingID: str,
                    user=Depends(userRequired)):

    data = DataRepository(database.db)

    verifyListingOwnership(data, listingID, user)

    createdSKU = data.createSKU(sku, listingID)

    return ListingResponses.SKU(meta={"id": createdSKU.id},
                                data=createdSKU)
