"""Contextos SSR para cadastro operacional de clientes e sites."""

from __future__ import annotations

from apps.smart_system.models import MaintenanceClient, OperationalSite
from apps.smart_system.services.tenant_scope import SmartSystemScopeService


def _serialize_client(client: MaintenanceClient) -> dict:
    sites = list(client.operational_sites.all())
    return {
        "code": str(client.public_id)[:8].upper(),
        "name": client.display_name,
        "document": client.document_number or "—",
        "email": client.contact_email or "—",
        "phone": client.contact_phone or "—",
        "status": "Ativo" if client.is_active else "Inativo",
        "status_slug": "active" if client.is_active else "inactive",
        "sites_count": len(sites),
    }


def _serialize_site(site: OperationalSite) -> dict:
    return {
        "code": str(site.public_id)[:8].upper(),
        "name": site.name,
        "address": site.address_line or "—",
        "city": site.city or "—",
        "state": site.state or "—",
        "contact_name": site.contact_name or "—",
        "contact_phone": site.contact_phone or "—",
        "status": "Ativo" if site.is_active else "Inativo",
    }


def get_customer_listing_context(*, request):
    queryset = SmartSystemScopeService.scope_queryset(
        MaintenanceClient.objects.prefetch_related("operational_sites"),
        request,
    ).order_by("display_name")
    rows = [_serialize_client(client) for client in queryset]
    return {
        "page_actions": [
            {
                "label": "Novo cliente",
                "route_name": "admin-shell:smart-system-customer-create",
                "permission_domain": "assets",
                "permission_action": "create",
            },
            {
                "label": "Novo site/unidade",
                "route_name": "admin-shell:smart-system-site-create",
                "permission_domain": "assets",
                "permission_action": "create",
            },
        ],
        "customers": rows,
    }


def get_customer_detail_context(*, request, customer_code: str):
    queryset = SmartSystemScopeService.scope_queryset(
        MaintenanceClient.objects.prefetch_related("operational_sites"),
        request,
    )
    client = queryset.filter(public_id__startswith=customer_code).first()
    if client is None:
        return None
    sites = [
        _serialize_site(site)
        for site in client.operational_sites.all().order_by("name")
    ]
    return {
        "customer": {
            "code": str(client.public_id)[:8].upper(),
            "name": client.display_name,
            "document": client.document_number or "—",
            "email": client.contact_email or "—",
            "phone": client.contact_phone or "—",
            "notes": client.notes or "",
            "status": "Ativo" if client.is_active else "Inativo",
        },
        "sites": sites,
        "page_actions": [
            {
                "label": "Editar cliente",
                "route_name": "admin-shell:smart-system-customer-update",
                "route_kwargs": {"customer_code": customer_code},
                "permission_domain": "assets",
                "permission_action": "update",
            },
            {
                "label": "Novo site/unidade",
                "route_name": "admin-shell:smart-system-site-create",
                "permission_domain": "assets",
                "permission_action": "create",
            },
        ],
    }
