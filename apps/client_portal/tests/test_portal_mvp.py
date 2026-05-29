import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.companies.models import Company, Membership, SiteMembership
from apps.smart_system.models import Asset, AssetCategory, MaintenanceClient, OperationalSite, ServiceOrder


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(
        email="cliente.portal@smart360.local",
        password="StrongPass123",
        first_name="Cliente",
    )


@pytest.fixture
def scoped_data(db, user):
    company = Company.objects.create(name="Cliente Portal", slug="cliente-portal")
    client = MaintenanceClient.objects.create(company=company, display_name="Cliente Portal")
    site = OperationalSite.objects.create(maintenance_client=client, name="Unidade A")
    category = AssetCategory.objects.create(name="Equipamentos Portal", slug="equipamentos-portal")
    asset = Asset.objects.create(
        operational_site=site,
        category=category,
        asset_tag="EQ-001",
        name="Compressor 01",
    )
    Membership.objects.create(user=user, company=company, is_primary=True)
    SiteMembership.objects.create(user=user, company=company, site=site, is_primary=True)
    return {"company": company, "client": client, "site": site, "asset": asset}


@pytest.mark.django_db
def test_anonymous_redirects_to_login(client):
    response = client.get(reverse("technical_portal:home"))

    assert response.status_code == 302
    assert response.url == "/login/?next=/portal/"


@pytest.mark.django_db
def test_authenticated_user_accesses_dashboard(client, user, scoped_data):
    client.force_login(user)

    response = client.get(reverse("technical_portal:home"))

    assert response.status_code == 200
    assert "Dashboard" in response.content.decode()


@pytest.mark.django_db
def test_create_service_order_via_post_creates_real_service_order(client, user, scoped_data):
    client.force_login(user)

    response = client.post(
        reverse("technical_portal:service-order-create"),
        {
            "operational_site": scoped_data["site"].pk,
            "asset": scoped_data["asset"].pk,
            "priority": ServiceOrder.Priority.HIGH,
            "description": "Equipamento parado no turno da manhã.",
        },
    )

    assert response.status_code == 302
    order = ServiceOrder.objects.get()
    assert order.client == scoped_data["client"]
    assert order.operational_site == scoped_data["site"]
    assert order.asset == scoped_data["asset"]
    assert order.status == ServiceOrder.Status.OPEN
    assert order.maintenance_type == ServiceOrder.MaintenanceType.CORRECTIVE
    assert order.order_number.startswith("SS-")


@pytest.mark.django_db
def test_common_user_cannot_access_out_of_scope_order(client, user, scoped_data):
    other_company = Company.objects.create(name="Outro Cliente", slug="outro-cliente")
    other_client = MaintenanceClient.objects.create(company=other_company, display_name="Outro Cliente")
    other_site = OperationalSite.objects.create(maintenance_client=other_client, name="Unidade Externa")
    order = ServiceOrder.objects.create(
        order_number="SS-FORA-0001",
        client=other_client,
        operational_site=other_site,
        maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
        priority=ServiceOrder.Priority.MEDIUM,
        status=ServiceOrder.Status.OPEN,
        source=ServiceOrder.Source.MANUAL,
        title="OS externa",
    )
    client.force_login(user)

    response = client.get(reverse("technical_portal:service-order-detail", args=[order.pk]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_main_routes_return_200(client, user, scoped_data):
    ServiceOrder.objects.create(
        order_number="SS-ROTA-0001",
        client=scoped_data["client"],
        operational_site=scoped_data["site"],
        asset=scoped_data["asset"],
        maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
        priority=ServiceOrder.Priority.MEDIUM,
        status=ServiceOrder.Status.OPEN,
        source=ServiceOrder.Source.MANUAL,
        title="Chamado em aberto",
    )
    order = ServiceOrder.objects.get(order_number="SS-ROTA-0001")
    client.force_login(user)

    urls = [
        reverse("technical_portal:home"),
        reverse("technical_portal:service-order-create"),
        reverse("technical_portal:service-orders"),
        reverse("technical_portal:service-order-detail", args=[order.pk]),
        reverse("technical_portal:assets"),
    ]

    for url in urls:
        assert client.get(url).status_code == 200
