from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any
from typing_extensions import Annotated, Union, Optional

from ..database.database import getDBSession
from ..functions import data
from ..models.categories import Category, SubCategory
from ..models.categories import Response as CategoryResponse

import cachetools.func
import sqlite3

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=CategoryResponse.Categories)
def getCategories(conn: sqlite3.Connection = Depends(getDBSession)):
    """
    Get all categories on the platform
    :param conn: Dependent, the connection to the database
    :return:  A list of all categories with metadata
    """

    # Get all categories from the database
    categories = data.getAllCategories(conn)
    total = len(categories)

    print(type(categories))

    return CategoryResponse.Categories(meta={
        'total': total
    },
        data=categories
    )

