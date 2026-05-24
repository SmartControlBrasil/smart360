"""Regras de acesso ao CRUD minimal de tenants (Company) no Admin Shell."""

from __future__ import annotations

from django.db.models import QuerySet
from django.utils import timezone

from apps.access_control_center.services.smart_system_access import (
    get_default_company_for_user,
    has_smart_system_permission,
)

from apps.companies.models import Company, Membership


def user_can_open_company_shell(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if has_smart_system_permission(
        user,
        "billing_admin",
        "view",
        company=get_default_company_for_user(user),
    ):
        return True
    return Membership.objects.filter(
        user=user, status=Membership.Status.ACTIVE, company__status=Company.Status.ACTIVE
    ).exists()


def user_can_create_saas_company(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    resolved = None if getattr(user, "is_superuser", False) else get_default_company_for_user(user)
    return has_smart_system_permission(user, "billing_admin", "manage", company=resolved)


def scoped_companies_for_user(user) -> QuerySet:
    qs = Company.objects.all().order_by("name")
    if getattr(user, "is_superuser", False):
        return qs
    if has_smart_system_permission(
        user,
        "billing_admin",
        "view",
        company=get_default_company_for_user(user),
    ):
        return qs
    ids = Membership.objects.filter(
        user=user, status=Membership.Status.ACTIVE, company__status=Company.Status.ACTIVE
    ).values_list("company_id", flat=True)
    return qs.filter(id__in=list(ids))


def user_can_manage_company_record(user, company: Company) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    if has_smart_system_permission(
        user,
        "billing_admin",
        "manage",
        company=get_default_company_for_user(user),
    ):
        return True
    return Membership.objects.filter(
        user=user,
        company=company,
        status=Membership.Status.ACTIVE,
        company__status=Company.Status.ACTIVE,
    ).exists()


def attach_primary_membership(user, company: Company) -> Membership:
    membership, _ = Membership.objects.update_or_create(
        user=user,
        company=company,
        defaults={
            "status": Membership.Status.ACTIVE,
            "is_primary": True,
            "joined_at": timezone.now(),
        },
    )
    return membership
