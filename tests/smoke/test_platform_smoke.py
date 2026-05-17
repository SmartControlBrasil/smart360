import pytest


@pytest.mark.django_db
@pytest.mark.smoke
def test_healthcheck_endpoint(client):
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "degraded"}


@pytest.mark.django_db
@pytest.mark.smoke
def test_healthcheck_details_endpoint(client):
    response = client.get("/health/details/")
    assert response.status_code == 200
    assert "checks" in response.json()


@pytest.mark.django_db
@pytest.mark.smoke
def test_api_root_endpoint(client):
    response = client.get("/api/v1/")
    assert response.status_code == 200
    assert "modules" in response.json()


@pytest.mark.django_db
@pytest.mark.smoke
def test_docs_endpoints(client):
    assert client.get("/api/schema/").status_code == 200
    assert client.get("/api/docs/").status_code == 200
    assert client.get("/api/redoc/").status_code == 200
