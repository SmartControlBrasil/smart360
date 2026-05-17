import pytest

from tests.factories.billing import InvoiceFactory


@pytest.mark.django_db
@pytest.mark.api
def test_billing_invoices_list(authenticated_api_client):
    InvoiceFactory()
    response = authenticated_api_client.get("/api/v1/billing/invoices/")
    assert response.status_code == 200
    assert response.json()["count"] >= 1

