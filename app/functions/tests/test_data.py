
from app.functions import data
from app.models.listings import Listing
from app.models.users import User


def test_idsToListings(mocker):
    """
    Test the idsToListings function
    """

    mocker.patch('app.database.databaseQueries.Queries.Listings.getListingsByIDs', return_value=[{
        'id': '0',
        'title': 'Test Listing',
        'description': 'A test listing',
        'basePrice': 100,
        'views': 0,
        'multipleSKUs': False,
        'hasDiscount': False,
        'category': 'test',
        'rating': 5,
        'subCategory': 'test',
        'addedAt': 0,
        'ownerUser': '{"id": "0", "username": "test", "profileURL": "test", "profilePictureURL": "test", "bannerURL": '
                     '"test", "description": "test", "joinedAt": 0}',
        'skus': '[]'

    }])

    listings = data.idsToListings(None, [0])

    Listing(
        id=0,
        title='Test Listing',
        description='A test listing',
        basePrice=100,
        views=0,
        multipleSKUs=False,
        hasDiscount=False,
        category='test',
        rating=5,
        subCategory='test',
        addedAt=0,
        ownerUser=User(
            id='0',
            username='test',
            profileURL='test',
            profilePictureURL='test',
            bannerURL='test',
            description='test',
            joinedAt=0
        )
    ), "Listing model format conversion is incorrect"

