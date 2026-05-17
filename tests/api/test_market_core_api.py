import pytest

from tests.factories.market_core import MarketplaceProductFactory, MarketplaceVendorFactory


@pytest.mark.django_db
@pytest.mark.api
def test_market_core_entities_exposed_via_caneca_module(authenticated_api_client):
    MarketplaceVendorFactory()
    MarketplaceProductFactory()
    vendors_response = authenticated_api_client.get("/api/v1/caneca-de-garagem/vendors/")
    products_response = authenticated_api_client.get("/api/v1/caneca-de-garagem/products/")
    assert vendors_response.status_code == 200
    assert products_response.status_code == 200

