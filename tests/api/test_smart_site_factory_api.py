import pytest

from tests.factories.smart_site_factory import NicheFactory


@pytest.mark.django_db
@pytest.mark.api
def test_site_factory_niches_list(authenticated_api_client):
    NicheFactory()
    response = authenticated_api_client.get("/api/v1/site-factory/niches/")
    assert response.status_code == 200
    assert response.json()["count"] >= 1

