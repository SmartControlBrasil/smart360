from __future__ import annotations

from decimal import Decimal

from apps.smart_system.models import QuoteItem, ServiceQuote
from apps.smart_system.services.tenant_scope import SmartSystemScopeService


def _scoped_quotes(request, tenant_context=None):
    queryset = SmartSystemScopeService.scope_related_queryset(ServiceQuote, request).select_related(
        "company",
        "operational_site",
        "work_order",
        "asset",
        "approved_by_user",
        "created_by",
    ).prefetch_related("items", "items__stock_item")
    tenant_context = tenant_context or {}
    company = tenant_context.get("company")
    site = tenant_context.get("site")
    if company is not None:
        queryset = queryset.filter(company=company)
    if site is not None:
        queryset = queryset.filter(operational_site=site)
    return queryset


def get_quote_listing_context(request, tenant_context=None, filters=None):
    filters = filters or {}
    queryset = _scoped_quotes(request, tenant_context=tenant_context)
    if filters.get("status"):
        queryset = queryset.filter(status=filters["status"])
    if filters.get("search"):
        term = filters["search"]
        queryset = (
            queryset.filter(work_order__order_number__icontains=term)
            | queryset.filter(quote_number__icontains=term)
        ).distinct()
    records = list(queryset.order_by("-created_at"))
    approved_value = sum((quote.total_value for quote in queryset.filter(status=ServiceQuote.Status.APPROVED)), Decimal("0"))
    return {
        "quote_filters": filters,
        "quote_records": records,
        "quote_kpis": [
            {"label": "Pendentes", "value": queryset.filter(status=ServiceQuote.Status.SENT).count(), "meta": "aguardando cliente", "tone": "amber"},
            {"label": "Aprovados", "value": queryset.filter(status=ServiceQuote.Status.APPROVED).count(), "meta": "liberados para execucao", "tone": "emerald"},
            {"label": "Rejeitados", "value": queryset.filter(status=ServiceQuote.Status.REJECTED).count(), "meta": "retidos ou em revisao", "tone": "rose"},
            {"label": "Valor aprovado", "value": f"R$ {approved_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), "meta": "periodo carregado", "tone": "indigo"},
        ],
        "page_actions": [],
    }


def get_quote_detail_context(request, quote_number, tenant_context=None):
    quote = _scoped_quotes(request, tenant_context=tenant_context).filter(quote_number=quote_number).first()
    if quote is None:
        return None
    items = list(quote.items.select_related("stock_item").all())
    return {
        "quote": quote,
        "quote_items": items,
        "part_items": [item for item in items if item.item_type == QuoteItem.ItemType.PART],
        "labor_items": [item for item in items if item.item_type == QuoteItem.ItemType.LABOR],
        "service_items": [item for item in items if item.item_type == QuoteItem.ItemType.SERVICE],
        "summary_cards": [
            {"label": "Status", "value": quote.get_status_display(), "meta": "estado comercial"},
            {"label": "Total pecas", "value": f"R$ {quote.total_parts:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), "meta": "itens de estoque"},
            {"label": "Total mao de obra", "value": f"R$ {quote.total_labor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), "meta": "servico tecnico"},
            {"label": "Total geral", "value": f"R$ {quote.total_value:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."), "meta": "valor proposto"},
        ],
        "page_actions": [
            {"label": "Enviar para cliente", "href": f"/app/smart-system/quotes/{quote.quote_number}/send/", "permission_domain": "quotes", "permission_action": "send"},
            {"label": "Aprovar internamente", "href": f"/app/smart-system/quotes/{quote.quote_number}/approve/", "permission_domain": "quotes", "permission_action": "approve"},
            {"label": "Rejeitar", "href": f"/app/smart-system/quotes/{quote.quote_number}/reject/", "permission_domain": "quotes", "permission_action": "reject"},
            {"label": "Abrir OS", "route_name": "admin-shell:smart-system-work-order-detail", "route_kwargs": {"order_code": quote.work_order.order_number}, "permission_domain": "work_orders", "permission_action": "view"},
        ],
    }
