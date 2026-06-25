from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.companies.models import Company, Membership, SiteMembership
from apps.smart_system.models import Asset, AssetCategory, MaintenanceClient, OperationalSite, ScheduledVisit, ServiceOrder
from apps.technical_portal.services import get_next_portal_visit, get_service_order_portal_visit


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


@pytest.fixture
def portal_request(user):
    request = RequestFactory().get("/portal/")
    request.user = user
    request.session = {}
    return request


def _local_display(value):
    return timezone.localtime(value).strftime("%d/%m/%Y %H:%M")


def _create_order(scoped_data, *, order_number, scheduled_start=None):
    return ServiceOrder.objects.create(
        order_number=order_number,
        client=scoped_data["client"],
        operational_site=scoped_data["site"],
        asset=scoped_data["asset"],
        maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
        priority=ServiceOrder.Priority.MEDIUM,
        status=ServiceOrder.Status.OPEN,
        source=ServiceOrder.Source.MANUAL,
        title=f"Chamado {order_number}",
        scheduled_start=scheduled_start,
    )


def _create_visit(scoped_data, *, work_order, scheduled_start, title="Visita tecnica"):
    return ScheduledVisit.objects.create(
        company=scoped_data["company"],
        operational_site=scoped_data["site"],
        asset=scoped_data["asset"],
        work_order=work_order,
        title=title,
        scheduled_date=scheduled_start.date(),
        scheduled_start=scheduled_start,
        status=ScheduledVisit.Status.SCHEDULED,
        source_type=ScheduledVisit.SourceType.WORK_ORDER,
    )



@pytest.mark.django_db
def test_dashboard_shows_next_visit_from_scheduled_visit(client, user, scoped_data):
    order = _create_order(
        scoped_data,
        order_number="SS-VIS-0001",
        scheduled_start=timezone.now() + timedelta(days=5),
    )
    visit_start = timezone.now() + timedelta(days=2)
    _create_visit(scoped_data, work_order=order, scheduled_start=visit_start)

    client.force_login(user)
    response = client.get(reverse("technical_portal:home"))

    assert response.status_code == 200
    content = response.content.decode()
    assert _local_display(visit_start) in content
    assert _local_display(timezone.now() + timedelta(days=5)) not in content


@pytest.mark.django_db
def test_dashboard_falls_back_to_service_order_scheduled_start(client, user, scoped_data):
    fallback_start = timezone.now() + timedelta(days=1)
    _create_order(scoped_data, order_number="SS-FBK-0001", scheduled_start=fallback_start)

    client.force_login(user)
    response = client.get(reverse("technical_portal:home"))

    assert response.status_code == 200
    assert _local_display(fallback_start) in response.content.decode()


@pytest.mark.django_db
def test_out_of_scope_scheduled_visit_is_not_visible(client, user, scoped_data, portal_request):
    own_start = timezone.now() + timedelta(days=1)
    own_order = _create_order(scoped_data, order_number="SS-OWN-0001", scheduled_start=own_start)

    other_company = Company.objects.create(name="Outro Cliente", slug="outro-cliente")
    other_client = MaintenanceClient.objects.create(company=other_company, display_name="Outro Cliente")
    other_site = OperationalSite.objects.create(maintenance_client=other_client, name="Unidade Externa")
    other_order = ServiceOrder.objects.create(
        order_number="SS-EXT-0001",
        client=other_client,
        operational_site=other_site,
        maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
        priority=ServiceOrder.Priority.MEDIUM,
        status=ServiceOrder.Status.OPEN,
        source=ServiceOrder.Source.MANUAL,
        title="OS externa",
    )
    external_start = timezone.now() + timedelta(days=3)
    ScheduledVisit.objects.create(
        company=other_company,
        operational_site=other_site,
        work_order=other_order,
        title="Visita externa",
        scheduled_date=external_start.date(),
        scheduled_start=external_start,
        status=ScheduledVisit.Status.SCHEDULED,
        source_type=ScheduledVisit.SourceType.WORK_ORDER,
    )

    request = portal_request
    next_visit = get_next_portal_visit(request)

    assert next_visit is not None
    assert next_visit.order_number == own_order.order_number
    assert _local_display(external_start) not in next_visit.display_at

    client.force_login(user)
    response = client.get(reverse("technical_portal:home"))
    assert response.status_code == 200
    content = response.content.decode()
    assert _local_display(own_start) in content
    assert _local_display(external_start) not in content


@pytest.mark.django_db
def test_client_cannot_access_internal_scheduling_calendar(client, user, scoped_data):
    client.force_login(user)

    response = client.get("/app/smart-system/scheduling/calendar/")

    assert response.status_code in {302, 403}


@pytest.mark.django_db
def test_service_order_detail_shows_next_visit_from_scheduled_visit(client, user, scoped_data, portal_request):
    order = _create_order(scoped_data, order_number="SS-DTL-0001")
    visit_start = timezone.now() + timedelta(days=4)
    _create_visit(scoped_data, work_order=order, scheduled_start=visit_start)

    visit = get_service_order_portal_visit(portal_request, order)
    assert visit is not None
    assert visit.display_at == _local_display(visit_start)

    client.force_login(user)
    response = client.get(reverse("technical_portal:service-order-detail", args=[order.pk]))

    assert response.status_code == 200
    assert _local_display(visit_start) in response.content.decode()
    assert "Próxima visita técnica" in response.content.decode()
