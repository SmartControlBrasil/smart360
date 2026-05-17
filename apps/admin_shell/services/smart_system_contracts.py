from __future__ import annotations

from decimal import Decimal

from apps.billing.models import Invoice
from apps.smart_system.models import MaintenanceContract, ServiceOrder
from apps.smart_system.services.tenant_scope import SmartSystemScopeService


def _scoped_contracts(request, tenant_context=None):
    queryset = SmartSystemScopeService.scope_related_queryset(MaintenanceContract, request).select_related(
        "company",
        "client",
        "operational_site",
    ).prefetch_related("covered_assets", "covered_assets__asset")
    tenant_context = tenant_context or {}
    company = tenant_context.get("company")
    site = tenant_context.get("site")
    if company is not None:
        queryset = queryset.filter(company=company)
    if site is not None:
        queryset = queryset.filter(operational_site=site)
    return queryset


def get_contract_listing_context(request, tenant_context=None, filters=None):
    filters = filters or {}
    queryset = _scoped_contracts(request, tenant_context=tenant_context)
    if filters.get("status"):
        queryset = queryset.filter(status=filters["status"])
    if filters.get("search"):
        term = filters["search"]
        queryset = queryset.filter(contract_number__icontains=term) | queryset.filter(client__display_name__icontains=term)
        queryset = queryset.distinct()
    records = list(queryset.order_by("-created_at"))
    recurring_value = sum((contract.contract_value for contract in queryset.filter(status=MaintenanceContract.Status.ACTIVE)), Decimal("0"))
    expiring_count = sum(1 for contract in records if contract.end_date)
    return {
        "contract_filters": filters,
        "contract_records": records,
        "contract_kpis": [
            {"label": "Contratos ativos", "value": queryset.filter(status=MaintenanceContract.Status.ACTIVE).count(), "meta": "clientes cobertos", "tone": "emerald"},
            {"label": "Valor recorrente", "value": f"R$ {recurring_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), "meta": "carteira ativa", "tone": "indigo"},
            {"label": "Clientes com contrato", "value": queryset.values("client_id").distinct().count(), "meta": "tenants atendidos", "tone": "sky"},
            {"label": "Com vencimento", "value": expiring_count, "meta": "acompanhar renovacao", "tone": "amber"},
        ],
        "page_actions": [],
    }


def get_contract_detail_context(request, contract_number, tenant_context=None):
    contract = _scoped_contracts(request, tenant_context=tenant_context).filter(contract_number=contract_number).first()
    if contract is None:
        return None
    covered_assets = list(contract.covered_assets.select_related("asset", "asset__category", "asset__operational_site").all())
    preventive_orders = list(
        ServiceOrder.objects.filter(maintenance_contract=contract)
        .select_related("asset", "operational_site", "assigned_to")
        .order_by("-opened_at")[:8]
    )
    invoices = list(
        Invoice.objects.filter(metadata__maintenance_contract_number=contract.contract_number)
        .select_related("billing_customer")
        .order_by("-issued_at")[:8]
    )
    return {
        "contract": contract,
        "contract_assets": covered_assets,
        "contract_orders": preventive_orders,
        "contract_invoices": invoices,
        "summary_cards": [
            {"label": "Status", "value": contract.get_status_display(), "meta": "estado do contrato"},
            {"label": "Valor", "value": f"R$ {contract.contract_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), "meta": contract.get_billing_frequency_display()},
            {"label": "Ativos cobertos", "value": len(covered_assets), "meta": "escopo operacional"},
            {"label": "Proxima cobranca", "value": contract.next_billing_date.strftime("%d/%m/%Y") if contract.next_billing_date else "-", "meta": "ciclo recorrente"},
        ],
        "page_actions": [],
    }
