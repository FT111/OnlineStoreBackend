from fastapi.testclient import TestClient

from app.database.database import getDBSession

testClient = TestClient(app)
testClient.app.dependency_overrides[getDBSession] = getTestDBSession


def test_get_listing():
	"""
	Test getting a listing
	"""
	response = testClient.get("/listings/1")
	assert response.status_code == 200
	assert response.json() == {
		"meta": {},
		"data": {
			"id": "1",
			"title": "Test Listing",
			"description": "A test listing",
			"basePrice": 100,
			"category": "test",
			"rating": 5,
			"subCategory": "test",
			"addedAt": 0,
			"ownerUser": None,
		}
	}
