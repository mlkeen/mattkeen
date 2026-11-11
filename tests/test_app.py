import pytest
from app import create_app


@pytest.fixture()
def client():
    app = create_app({"TESTING": True})
    return app.test_client()


def test_home(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Data analysis for real-world decisions" in response.data


def test_rail_project(client):
    response = client.get("/projects/intercity-rail")
    assert response.status_code == 200
    assert b"U.S. Intercity Rail Explorer" in response.data


def test_route_api(client):
    response = client.get("/api/rail/routes/downeaster")
    assert response.status_code == 200
    assert response.get_json()["name"] == "Downeaster"


def test_missing_route(client):
    assert client.get("/projects/intercity-rail/routes/nope").status_code == 404
