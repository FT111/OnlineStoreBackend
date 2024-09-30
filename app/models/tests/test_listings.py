from ..listings import Listing
import pytest
from pydantic import ValidationError


def test_listing():
    """
    Test the validation of a listing
    """

    listing = Listing(
        id=0,
        title="Test Listing",
        description="A test listing",
        basePrice=100,
        category="test",
        rating=5,
        subCategory="test",
        addedAt=0,
        ownerUser=None,
    )


def test_listing_invalid_rating():
    """
    Test the validation of a listing with an invalid rating
    """

    with pytest.raises(ValidationError):
        Listing(
            id=0,
            title="Test Listing",
            description="A test listing",
            basePrice=100,
            category="test",
            rating=6,
            subCategory="test",
            addedAt=0,
            ownerUser=None,
        )
