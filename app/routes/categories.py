import sqlite3

from fastapi import APIRouter, Depends

from ..database.database import getDBSession
from ..functions.data import DataRepository
from ..models.categories import Response as CategoryResponse

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=CategoryResponse.Categories)
def getCategories(conn: sqlite3.Connection = Depends(getDBSession)):
    """
    Get all categories on the platform
    :param conn: Dependent, the connection to the database
    :return:  A list of all categories with metadata
    """

    data = DataRepository(conn)

    # Get all categories from the database
    categories = data.getAllCategories()
    total = len(categories)

    return CategoryResponse.Categories(meta={
        'total': total
    },
        data=categories
    )


@router.get("/{categoryTitle}", response_model=CategoryResponse.Category)
def getCategory(categoryTitle: str):
    """
    
    :param categoryTitle:
    :return:
    """

    data = DataRepository(conn)

    category = data.getCategory(categoryTitle)

    return CategoryResponse.Category(meta={

    },
        data=category
    )
