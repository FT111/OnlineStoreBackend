from fastapi import APIRouter

from ..database import database
from ..functions.data import DataRepository
from ..models.categories import Response as CategoryResponse

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=CategoryResponse.Categories)
def getCategories():
	"""
	Get all categories on the platform
	:param conn: Dependent, the connection to the database
	:return:  A list of all categories with metadata
	"""

	data = DataRepository(database.dbQueue)

	# Get all categories from the database
	categories = data.getAllCategories()
	total = len(categories)

	return CategoryResponse.Categories(meta={
		'total': total
	},
		data=categories
	)


@router.get("/{categoryTitle}", response_model=CategoryResponse.Category)
def getCategory(categoryTitle: str,
				):
	"""

	:param conn: The connection to the database
	:param categoryTitle:
	:return:
	"""

	data = DataRepository(database.dbQueue)

	category = data.getCategory(categoryTitle)

	return CategoryResponse.Category(meta={

	},
		data=category
	)
