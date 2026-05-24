"""
Registro inicial SaaS: Company + primeiro usuario administrador + Membership primaria.

Nao faz login nem manipula sessao HTTP — isso permanece na view.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.access_control_center.models import Role
from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.companies.models import Company, Membership

User = get_user_model()


def _digits_payload(value: str) -> str:
    return "".join(c for c in (value or "") if c.isdigit())


def company_tax_digits_conflict(candidate_tax_id: str) -> bool:
    """True se alguma Company existe com mesmo documento apenas-numerico (nao-vazio)."""
    candidate = _digits_payload(candidate_tax_id)
    if not candidate:
        return False
    qs = Company.objects.exclude(tax_id="").values_list("tax_id", flat=True).iterator()
    for stored in qs:
        if _digits_payload(stored) == candidate:
            return True
    return False


def ensure_company_admin_assignment(user, *, company):
    """Garante RBAC bootstrap e perfil gestor dentro da empresa (escopo COMPANY)."""
    if not Role.objects.filter(slug="company-admin").exists():
        bootstrap_smart_system_access()
    assign_smart_system_role(user, "company-admin", company=company)


def _allocate_slug(base_name: str) -> str:
    """Slug unico derivado do nome fantasia."""
    root = slugify(base_name)[:175] or "empresa"
    candidate = root
    n = 1
    while Company.objects.filter(slug=candidate).exists():
        candidate = f"{root}-{n}"[:180]
        n += 1
    return candidate


@transaction.atomic
def register_company_and_primary_admin(*, form) -> tuple[User, Company]:
    """
    Cria Company ativa, User (cliente) e Membership principal.

    Espera formulario ja validado (SaasTenantRegistrationForm).
    """
    first_name, last_name = form.split_admin_name_for_user()
    slug = _allocate_slug(form.cleaned_data["company_name"])
    now = timezone.now()

    company = Company.objects.create(
        name=form.cleaned_data["company_name"],
        legal_name=(form.cleaned_data.get("legal_name") or "").strip(),
        slug=slug,
        tax_id=form.cleaned_data.get("tax_id") or "",
        email=form.cleaned_data.get("company_email") or "",
        phone_number=(form.cleaned_data.get("phone_number") or "").strip(),
        website=form.cleaned_data.get("website") or "",
        city=(form.cleaned_data.get("city") or "").strip(),
        state=(form.cleaned_data.get("state") or "").strip(),
        status=Company.Status.ACTIVE,
    )

    user = User.objects.create_user(
        email=form.cleaned_data["admin_email"],
        password=form.cleaned_data["password1"],
        first_name=first_name,
        last_name=last_name,
        user_type=User.UserType.CLIENT,
        is_staff=False,
        is_active=True,
    )

    Membership.objects.create(
        user=user,
        company=company,
        status=Membership.Status.ACTIVE,
        is_primary=True,
        invited_at=None,
        joined_at=now,
    )

    ensure_company_admin_assignment(user, company=company)

    return user, company
