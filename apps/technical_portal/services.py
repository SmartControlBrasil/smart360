from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.access_control_center.models import UserRoleAssignment
from apps.smart_system.models import Asset, OperationalSite, ScheduledVisit, ServiceOrder
from apps.smart_system.services.tenant_scope import SmartSystemScopeService


SERVICE_ORDER_CREATE_ROLE_SLUGS = {
    "client-admin",
    "client-manager",
    "company-admin",
    "maintenance-manager",
    "manager",
    "requester",
}

ACTIVE_SCHEDULED_VISIT_STATUSES = {
    ScheduledVisit.Status.PENDING_ASSIGNMENT,
    ScheduledVisit.Status.SCHEDULED,
    ScheduledVisit.Status.CONFIRMED,
    ScheduledVisit.Status.IN_PROGRESS,
}


@dataclass(frozen=True)
class ClientPortalVisitDisplay:
    scheduled_at: datetime
    order_number: str
    asset_label: str

    @property
    def display_at(self) -> str:
        return timezone.localtime(self.scheduled_at).strftime("%d/%m/%Y %H:%M")


def portal_queryset(queryset: QuerySet, request) -> QuerySet:
    user = request.user
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return queryset
    return SmartSystemScopeService.scope_queryset(queryset, request)


def allowed_sites(request) -> QuerySet:
    return portal_queryset(
        OperationalSite.objects.select_related("maintenance_client", "maintenance_client__company"),
        request,
    )


def allowed_assets(request) -> QuerySet:
    return portal_queryset(
        Asset.objects.select_related("operational_site", "category", "operational_site__maintenance_client"),
        request,
    )


def allowed_service_orders(request) -> QuerySet:
    return portal_queryset(
        ServiceOrder.objects.select_related("client", "operational_site", "asset", "created_by"),
        request,
    )


def allowed_scheduled_visits(request) -> QuerySet:
    return portal_queryset(
        ScheduledVisit.objects.select_related(
            "work_order",
            "work_order__asset",
            "asset",
            "operational_site",
            "operational_site__maintenance_client",
        ).filter(work_order__isnull=False),
        request,
    )


def user_can_access_service_order(request, service_order: ServiceOrder) -> bool:
    return allowed_service_orders(request).filter(pk=service_order.pk).exists()


def user_can_create_service_order(request) -> bool:
    user = request.user
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True

    allowed_company_ids = SmartSystemScopeService.get_allowed_company_ids(user)
    if not allowed_company_ids:
        return False

    if user.groups.filter(name__in=SERVICE_ORDER_CREATE_ROLE_SLUGS).exists():
        return True

    return UserRoleAssignment.objects.filter(
        user=user,
        is_active=True,
        role__is_active=True,
        role__slug__in=SERVICE_ORDER_CREATE_ROLE_SLUGS,
        company_id__in=allowed_company_ids,
    ).exists()


def _visit_effective_datetime(visit: ScheduledVisit) -> datetime:
    if visit.scheduled_start:
        return visit.scheduled_start
    tz = timezone.get_current_timezone()
    window = visit.window_start or time.min
    return timezone.make_aware(datetime.combine(visit.scheduled_date, window), tz)


def upcoming_scheduled_visits(request) -> QuerySet:
    now = timezone.now()
    today = timezone.localdate()
    return (
        allowed_scheduled_visits(request)
        .filter(status__in=ACTIVE_SCHEDULED_VISIT_STATUSES)
        .filter(Q(scheduled_start__gte=now) | Q(scheduled_start__isnull=True, scheduled_date__gte=today))
        .order_by("scheduled_date", "scheduled_start", "route_order", "pk")
    )


def _asset_label_for_visit(visit: ScheduledVisit) -> str:
    asset = visit.asset
    if asset is None and visit.work_order_id:
        asset = visit.work_order.asset
    return getattr(asset, "name", "") or ""


def _from_scheduled_visit(visit: ScheduledVisit) -> ClientPortalVisitDisplay:
    work_order = visit.work_order
    return ClientPortalVisitDisplay(
        scheduled_at=_visit_effective_datetime(visit),
        order_number=getattr(work_order, "order_number", "") or "",
        asset_label=_asset_label_for_visit(visit),
    )


def _from_service_order(order: ServiceOrder) -> ClientPortalVisitDisplay | None:
    if not order.scheduled_start or order.scheduled_start < timezone.now():
        return None
    return ClientPortalVisitDisplay(
        scheduled_at=order.scheduled_start,
        order_number=order.order_number,
        asset_label=getattr(order.asset, "name", "") or "",
    )


def get_service_order_portal_visit(request, service_order: ServiceOrder) -> ClientPortalVisitDisplay | None:
    visits = list(upcoming_scheduled_visits(request).filter(work_order=service_order)[:20])
    if visits:
        visit = min(visits, key=_visit_effective_datetime)
        return _from_scheduled_visit(visit)
    return _from_service_order(service_order)


def get_next_portal_visit(request) -> ClientPortalVisitDisplay | None:
    visits = list(upcoming_scheduled_visits(request)[:50])
    if visits:
        visit = min(visits, key=_visit_effective_datetime)
        return _from_scheduled_visit(visit)
    order = next_service_order_visit(request)
    if order:
        return _from_service_order(order)
    return None


def attach_portal_visits_to_orders(request, orders) -> None:
    order_list = list(orders)
    if not order_list:
        return

    order_ids = [order.pk for order in order_list]
    visits = list(upcoming_scheduled_visits(request).filter(work_order_id__in=order_ids))
    earliest_by_order: dict[int, ScheduledVisit] = {}
    for visit in visits:
        current = earliest_by_order.get(visit.work_order_id)
        if current is None or _visit_effective_datetime(visit) < _visit_effective_datetime(current):
            earliest_by_order[visit.work_order_id] = visit

    now = timezone.now()
    for order in order_list:
        visit = earliest_by_order.get(order.pk)
        if visit:
            order.portal_next_visit = _from_scheduled_visit(visit)
        elif order.scheduled_start and order.scheduled_start >= now:
            order.portal_next_visit = _from_service_order(order)
        else:
            order.portal_next_visit = None


def upcoming_service_orders(request) -> QuerySet:
    return (
        allowed_service_orders(request)
        .filter(scheduled_start__gte=timezone.now())
        .order_by("scheduled_start", "opened_at")
    )


def next_service_order_visit(request) -> ServiceOrder | None:
    return upcoming_service_orders(request).first()
