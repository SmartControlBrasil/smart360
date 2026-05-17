from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.billing.models import BillingPlan, Contract, Invoice, Subscription
from apps.billing.services.billing_service import BillingDashboardService


def _money(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _status_tone(status):
    mapping = {
        "active": "emerald",
        "trial": "sky",
        "trialing": "sky",
        "pending": "amber",
        "open": "amber",
        "suspended": "red",
        "cancelled": "slate",
        "expired": "slate",
        "overdue": "red",
        "paid": "emerald",
        "inactive": "slate",
        "archived": "slate",
    }
    return mapping.get(status, "indigo")


def _normalize_plan(plan):
    features = plan.enabled_features if isinstance(plan.enabled_features, list) else []
    return {
        "name": plan.name,
        "slug": plan.slug,
        "description": plan.description or "Plano comercial da plataforma SMART360.",
        "price_monthly": _money(plan.price_monthly or plan.price_amount or Decimal("0.00")),
        "price_yearly": _money(plan.price_yearly or plan.price_amount or Decimal("0.00")),
        "user_limit": plan.user_limit or "Ilimitado",
        "asset_limit": plan.asset_limit or "Ilimitado",
        "site_limit": plan.site_limit or "Ilimitado",
        "work_order_limit": plan.work_order_limit or "Ilimitado",
        "features": features[:4],
        "status": plan.status,
        "tone": _status_tone(plan.status),
    }


def _normalize_contract(contract):
    subscription = contract.subscriptions.order_by("-started_at").first()
    latest_invoice = contract.invoices.order_by("-issued_at").first()
    return {
        "contract_code": contract.contract_code,
        "company_name": contract.company.name,
        "company_slug": contract.company.slug,
        "plan_name": contract.plan.name,
        "plan_slug": contract.plan.slug,
        "contracted_amount": _money(contract.contracted_amount),
        "billing_periodicity": contract.billing_periodicity,
        "status": contract.status,
        "status_tone": _status_tone(contract.status),
        "start_date": contract.start_date,
        "renewal_date": contract.renewal_date,
        "sales_owner": getattr(contract.sales_owner, "display_name", "") or getattr(contract.sales_owner, "full_name", "") or getattr(contract.sales_owner, "email", "Nao definido"),
        "subscription_status": subscription.status if subscription else "not_started",
        "subscription_status_tone": _status_tone(subscription.status if subscription else "inactive"),
        "latest_invoice_status": latest_invoice.status if latest_invoice else "not_issued",
        "latest_invoice_status_tone": _status_tone(latest_invoice.status if latest_invoice else "inactive"),
    }


def _normalize_invoice(invoice):
    return {
        "invoice_number": invoice.invoice_number,
        "company_name": invoice.company.name if invoice.company else invoice.billing_customer.trade_name,
        "contract_code": invoice.contract.contract_code if invoice.contract else "",
        "total_amount": _money(invoice.total_amount),
        "issued_at": invoice.issued_at,
        "due_at": invoice.due_at,
        "status": invoice.status,
        "status_tone": _status_tone(invoice.status),
        "payment_method": invoice.payment_method or "manual",
        "external_reference": invoice.external_reference,
    }


def get_billing_dashboard_context():
    summary = BillingDashboardService.get_summary()
    contracts = Contract.objects.select_related("company", "plan", "sales_owner").prefetch_related("subscriptions", "invoices")[:6]
    invoices = Invoice.objects.select_related("company", "contract", "billing_customer").order_by("-issued_at")[:8]
    plans = BillingPlan.objects.order_by("name")[:3]

    dashboard_widgets = [
        {"label": "MRR estimado", "value": _money(summary["mrr"]), "meta": "Receita recorrente mensal estimada", "tone": "emerald"},
        {"label": "Empresas ativas", "value": str(summary["active_companies"]), "meta": "Tenants com acesso liberado", "tone": "indigo"},
        {"label": "Trials ativos", "value": str(summary["trial_companies"]), "meta": "Empresas em periodo de avaliacao", "tone": "sky"},
        {"label": "Empresas inadimplentes", "value": str(summary["overdue_companies"]), "meta": "Demandam follow-up financeiro", "tone": "red"},
        {"label": "Contratos ativos", "value": str(summary["active_contracts"]), "meta": "Base contratual vigente", "tone": "violet"},
        {"label": "Faturas pendentes", "value": str(summary["pending_invoices"]), "meta": "Titulos aguardando liquidacao", "tone": "amber"},
        {"label": "Faturas pagas", "value": str(summary["paid_invoices"]), "meta": "Historico ja compensado", "tone": "emerald"},
    ]

    quick_actions = [
        {"label": "Novo contrato", "href": "#novo-contrato", "permission_domain": "billing_admin", "permission_action": "manage"},
        {"label": "Ver planos", "route_name": "admin-shell:billing-plans", "permission_domain": "billing_admin", "permission_action": "view"},
        {"label": "Gerir contratos", "route_name": "admin-shell:billing-contracts", "permission_domain": "billing_admin", "permission_action": "view"},
        {"label": "Revisar faturas", "route_name": "admin-shell:billing-invoices", "permission_domain": "billing_admin", "permission_action": "view"},
        {"label": "Exportar carteira", "href": "#exportar-billing", "permission_domain": "billing_admin", "permission_action": "export"},
    ]

    return {
        "billing_dashboard_widgets": dashboard_widgets,
        "billing_contracts_preview": [_normalize_contract(contract) for contract in contracts],
        "billing_invoices_preview": [_normalize_invoice(invoice) for invoice in invoices],
        "billing_plan_cards": [_normalize_plan(plan) for plan in plans],
        "page_actions": quick_actions,
    }


def get_billing_plan_context():
    plans = BillingPlan.objects.annotate(contract_count=Count("contracts")).order_by("name")
    active_plans = plans.filter(status=BillingPlan.Status.ACTIVE).count()
    active_contracts = Contract.objects.filter(status=Contract.Status.ACTIVE).count()
    return {
        "billing_plan_cards": [
            {
                **_normalize_plan(plan),
                "contract_count": plan.contract_count,
            }
            for plan in plans
        ],
        "billing_plan_kpis": [
            {"label": "Planos cadastrados", "value": str(plans.count()), "meta": "Catalogo comercial da plataforma", "tone": "indigo"},
            {"label": "Planos ativos", "value": str(active_plans), "meta": "Disponiveis para comercializacao", "tone": "emerald"},
            {"label": "Contratos vinculados", "value": str(active_contracts), "meta": "Empresas operando sob plano", "tone": "sky"},
        ],
    }


def get_billing_contract_context(filters=None):
    filters = filters or {}
    queryset = Contract.objects.select_related("company", "plan", "sales_owner").prefetch_related("subscriptions", "invoices").order_by("-start_date")

    search = filters.get("q", "").strip()
    if search:
        queryset = queryset.filter(
            Q(contract_code__icontains=search)
            | Q(company__name__icontains=search)
            | Q(plan__name__icontains=search)
        )
    if filters.get("status"):
        queryset = queryset.filter(status=filters["status"])
    if filters.get("periodicity"):
        queryset = queryset.filter(billing_periodicity=filters["periodicity"])

    contracts = [_normalize_contract(contract) for contract in queryset]
    return {
        "billing_contracts": contracts,
        "billing_contract_filters": [
            {"label": "Busca", "name": "q", "value": filters.get("q", ""), "type": "search", "placeholder": "Contrato, empresa ou plano"},
            {"label": "Status", "name": "status", "value": filters.get("status", ""), "type": "select", "options": ["active", "suspended", "cancelled", "expired"]},
            {"label": "Periodicidade", "name": "periodicity", "value": filters.get("periodicity", ""), "type": "select", "options": ["monthly", "yearly"]},
        ],
        "billing_contract_kpis": [
            {"label": "Contratos ativos", "value": str(queryset.filter(status=Contract.Status.ACTIVE).count()), "meta": "Base vigente", "tone": "emerald"},
            {"label": "Contratos suspensos", "value": str(queryset.filter(status=Contract.Status.SUSPENDED).count()), "meta": "Bloqueados financeiramente", "tone": "red"},
            {"label": "Renovacoes proximas", "value": str(queryset.filter(renewal_date__lte=timezone.localdate() + timedelta(days=30)).count()), "meta": "Ate 30 dias", "tone": "amber"},
        ],
    }


def get_contract_detail_context(contract_code):
    contract = (
        Contract.objects.select_related("company", "plan", "sales_owner", "billing_customer")
        .prefetch_related("subscriptions", "invoices")
        .filter(contract_code=contract_code)
        .first()
    )
    if contract is None:
        return None

    subscription = contract.subscriptions.order_by("-started_at").first()
    invoices = contract.invoices.select_related("company").order_by("-issued_at")
    invoice_rows = [_normalize_invoice(invoice) for invoice in invoices]

    return {
        "contract": {
            **_normalize_contract(contract),
            "notes": contract.notes,
            "company_email": contract.company.email,
            "billing_email": contract.billing_customer.billing_email if contract.billing_customer else contract.company.email,
            "metadata": contract.metadata,
            "page_actions": [
                {"label": "Suspender", "href": "#suspender", "permission_domain": "billing_admin", "permission_action": "manage"},
                {"label": "Cancelar", "href": "#cancelar", "permission_domain": "billing_admin", "permission_action": "manage"},
                {"label": "Ver faturas", "route_name": "admin-shell:billing-invoices", "permission_domain": "billing_admin", "permission_action": "view"},
                {"label": "Exportar", "href": "#exportar-contrato", "permission_domain": "billing_admin", "permission_action": "export"},
            ],
        },
        "billing_subscription_summary": {
            "status": subscription.status if subscription else "not_started",
            "status_tone": _status_tone(subscription.status if subscription else "inactive"),
            "next_billing_at": subscription.next_billing_at if subscription else None,
            "amount": _money(subscription.amount if subscription else contract.contracted_amount),
            "billing_method": subscription.billing_method if subscription else "manual",
            "current_period_start": subscription.current_period_start if subscription else None,
            "current_period_end": subscription.current_period_end if subscription else None,
        },
        "billing_invoice_rows": invoice_rows,
        "billing_contract_notes": [
            "Base preparada para integracao com gateway externo.",
            "Suspensao contratual impacta o bloqueio de acesso do tenant.",
            "Historico financeiro consolidado por empresa e contrato.",
        ],
    }


def get_billing_invoice_context(filters=None):
    filters = filters or {}
    queryset = Invoice.objects.select_related("company", "contract", "billing_customer").order_by("-issued_at")
    search = filters.get("q", "").strip()
    if search:
        queryset = queryset.filter(
            Q(invoice_number__icontains=search)
            | Q(company__name__icontains=search)
            | Q(contract__contract_code__icontains=search)
        )
    if filters.get("status"):
        queryset = queryset.filter(status=filters["status"])

    invoices = [_normalize_invoice(invoice) for invoice in queryset]
    pending_value = queryset.filter(status__in=[Invoice.Status.DRAFT, Invoice.Status.OPEN, Invoice.Status.OVERDUE]).aggregate(
        total=Sum("total_amount")
    )["total"] or Decimal("0.00")
    return {
        "billing_invoices": invoices,
        "billing_invoice_filters": [
            {"label": "Busca", "name": "q", "value": filters.get("q", ""), "type": "search", "placeholder": "Fatura, empresa ou contrato"},
            {"label": "Status", "name": "status", "value": filters.get("status", ""), "type": "select", "options": ["draft", "open", "paid", "overdue", "cancelled"]},
        ],
        "billing_invoice_kpis": [
            {"label": "Faturas emitidas", "value": str(queryset.count()), "meta": "Carteira filtrada", "tone": "indigo"},
            {"label": "Pendentes", "value": _money(pending_value), "meta": "Valor em aberto", "tone": "amber"},
            {"label": "Pagas", "value": str(queryset.filter(status=Invoice.Status.PAID).count()), "meta": "Titulos liquidados", "tone": "emerald"},
        ],
    }
