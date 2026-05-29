from __future__ import annotations

from django.db.models import QuerySet

from apps.smart_system.models import Asset, OperationalSite, ServiceOrder
from apps.smart_system.services.tenant_scope import SmartSystemScopeService


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
