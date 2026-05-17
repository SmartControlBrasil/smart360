"""Contexto para abertura de OS corretiva no Admin Shell (escopo Smart System)."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.companies.models import Membership
from apps.companies.services.tenant_scope import TenantScopeService
from apps.smart_system.models import Asset, MaintenancePlan
from apps.smart_system.services.tenant_scope import SmartSystemScopeService

from .tenant_scope import build_shell_tenant_context


User = get_user_model()


def scoped_assets_for_corrective_order(request):
    qs = (
        SmartSystemScopeService.scope_related_queryset(Asset, request)
        .filter(is_active=True)
        .select_related("operational_site", "operational_site__maintenance_client", "operational_site__maintenance_client__company", "category")
        .order_by("operational_site__name", "asset_tag")
    )
    shell = build_shell_tenant_context(request)
    site = shell.get("site")
    if site is not None:
        qs = qs.filter(operational_site_id=site.id)
    return qs


def assignable_users_for_corrective_order(request):
    shell = build_shell_tenant_context(request)
    company = shell.get("company")
    scope = SmartSystemScopeService.resolve_scope(request)
    if company is not None:
        user_ids = (
            Membership.objects.filter(company_id=company.id, status=Membership.Status.ACTIVE)
            .values_list("user_id", flat=True)
            .distinct()
        )
        return User.objects.filter(id__in=user_ids, is_active=True).order_by("first_name", "email")
    if scope.company_ids:
        user_ids = (
            Membership.objects.filter(company_id__in=scope.company_ids, status=Membership.Status.ACTIVE)
            .values_list("user_id", flat=True)
            .distinct()
        )
        return User.objects.filter(id__in=user_ids, is_active=True).order_by("first_name", "email")
    ctx = TenantScopeService.resolve_context(request)
    if ctx.company is not None:
        user_ids = (
            Membership.objects.filter(company_id=ctx.company.id, status=Membership.Status.ACTIVE)
            .values_list("user_id", flat=True)
            .distinct()
        )
        return User.objects.filter(id__in=user_ids, is_active=True).order_by("first_name", "email")
    return User.objects.none()


def build_corrective_work_order_create_context(request):
    assets = scoped_assets_for_corrective_order(request)
    return {
        "assets": assets,
        "asset_count": assets.count(),
        "assignable_users": assignable_users_for_corrective_order(request),
    }


def scoped_maintenance_plans_for_preventive_order(request):
    qs = (
        SmartSystemScopeService.scope_related_queryset(MaintenancePlan, request)
        .filter(is_active=True)
        .select_related(
            "operational_site",
            "operational_site__maintenance_client",
            "operational_site__maintenance_client__company",
            "asset",
            "asset__operational_site",
            "asset__operational_site__maintenance_client",
            "company",
        )
    )
    shell = build_shell_tenant_context(request)
    site = shell.get("site")
    if site is not None:
        qs = qs.filter(Q(operational_site_id=site.id) | Q(asset__operational_site_id=site.id))
    return qs.order_by("name")


def maintenance_plan_client_and_site(plan: MaintenancePlan):
    if plan.operational_site_id:
        site = plan.operational_site
        return site.maintenance_client, site
    if plan.asset_id:
        site = plan.asset.operational_site
        return site.maintenance_client, site
    return None, None


def assets_for_preventive_plan(plan: MaintenancePlan, request):
    base = scoped_assets_for_corrective_order(request)
    if plan.asset_id:
        return base.filter(pk=plan.asset_id)
    _client, site = maintenance_plan_client_and_site(plan)
    if site is not None:
        return base.filter(operational_site_id=site.id)
    return base.none()


def build_preventive_work_order_create_context(request):
    plans = scoped_maintenance_plans_for_preventive_order(request)
    return {
        "maintenance_plans": plans,
        "plan_count": plans.count(),
        "assignable_users": assignable_users_for_corrective_order(request),
    }
