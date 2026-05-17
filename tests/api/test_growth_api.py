import pytest

from tests.factories.growth import LeadFactory


@pytest.mark.django_db
@pytest.mark.api
def test_growth_leads_list(authenticated_api_client):
    LeadFactory()
    response = authenticated_api_client.get("/api/v1/growth/leads/")
    assert response.status_code == 200
    assert response.json()["count"] >= 1

