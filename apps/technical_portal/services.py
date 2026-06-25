from __future__ import annotations

from django.db.models import QuerySet
from django.utils import timezone

from apps.access_control_center.models import UserRoleAssignment
from apps.smart_system.models import Asset, OperationalSite, ServiceOrder
from apps.smart_system.services.tenant_scope import SmartSystemScopeService


SERVICE_ORDER_CREATE_ROLE_SLUGS = {
    "client-admin",
    "client-manager",
    "company-admin",
    "maintenance-manager",
    "manager",
    "requester",
}


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

    return UserRoleAssignment.objects.filter(
        user=user,
        is_active=True,
        role__is_active=True,
        role__slug__in=SERVICE_ORDER_CREATE_ROLE_SLUGS,
        company_id__in=allowed_company_ids,
    ).exists()


def upcoming_service_orders(request) -> QuerySet:
    return (
        allowed_service_orders(request)
        .filter(scheduled_start__gte=timezone.now())
        .order_by("scheduled_start", "opened_at")
    )


def next_service_order_visit(request) -> ServiceOrder | None:
    return upcoming_service_orders(request).first()
