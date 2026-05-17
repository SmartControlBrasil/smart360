import pytest

from tests.factories.smart_system import ServiceOrderFactory


@pytest.mark.django_db
@pytest.mark.api
def test_smart_system_service_orders_list(authenticated_api_client):
    ServiceOrderFactory()
    response = authenticated_api_client.get("/api/v1/smart-system/service-orders/")
    assert response.status_code == 200
    assert response.json()["count"] >= 1

