from __future__ import annotations

from datetime import timedelta
from django.db.models import Q
from django.utils import timezone

from apps.access_control_center.models import UserRoleAssignment
from apps.access_control_center.services.smart_system_access import filter_permissioned_items
from apps.billing.services.billing_service import BillingAccessService
from apps.smart_system.models import (
    Asset,
    ClientPortalRequest,
    FailureEvent,
    MaintenanceContract,
    MaintenancePlan,
    OperationalSite,
    ServiceQuote,
    ServiceOrder,
)
from apps.smart_system.services.tenant_scope import SmartSystemScopeService

from .smart_system_reports import generate_report_pdf, get_report_history_entries, get_report_preview_context


def get_client_portal_navigation(current_url_name="", permission_map=None):
    navigation = [
        {
            "label": "Visao Geral",
            "items": [
                {
                    "label": "Dashboard",
                    "url_name": "admin-shell:client-portal-dashboard",
                    "match_names": ["admin-shell:client-portal-dashboard"],
                    "permission_domain": "client_portal_dashboard",
                    "permission_action": "view",
                },
                {
                    "label": "AI Copilot",
                    "url_name": "admin-shell:client-portal-copilot",
                    "match_names": ["admin-shell:client-portal-copilot"],
                    "permission_domain": "client_portal_dashboard",
                    "permission_action": "view",
                },
                {
                    "label": "Unidades",
                    "url_name": "admin-shell:client-portal-sites",
                    "match_names": ["admin-shell:client-portal-sites"],
                    "permission_domain": "client_portal_sites",
                    "permission_action": "view",
                },
            ],
        },
        {
            "label": "Operacao",
            "items": [
                {
                    "label": "Ativos",
                    "url_name": "admin-shell:client-portal-assets",
                    "match_names": [
                        "admin-shell:client-portal-assets",
                        "admin-shell:client-portal-asset-detail",
                    ],
                    "permission_domain": "client_portal_assets",
                    "permission_action": "view",
                },
                {
                    "label": "Ordens de Servico",
                    "url_name": "admin-shell:client-portal-work-orders",
                    "match_names": [
                        "admin-shell:client-portal-work-orders",
                        "admin-shell:client-portal-work-order-detail",
                    ],
                    "permission_domain": "client_portal_work_orders",
                    "permission_action": "view",
                },
                {
                    "label": "Preventivas",
                    "url_name": "admin-shell:client-portal-preventives",
                    "match_names": [
                        "admin-shell:client-portal-preventives",
                        "admin-shell:client-portal-preventive-detail",
                    ],
                    "permission_domain": "client_portal_preventives",
                    "permission_action": "view",
                },
                {
                    "label": "Relatorios",
                    "url_name": "admin-shell:client-portal-reports",
                    "match_names": [
                        "admin-shell:client-portal-reports",
                        "admin-shell:client-portal-report-preview",
                    ],
                    "permission_domain": "client_portal_reports",
                    "permission_action": "view",
                },
                {
                    "label": "Orcamentos",
                    "url_name": "admin-shell:client-portal-quotes",
                    "match_names": [
                        "admin-shell:client-portal-quotes",
                        "admin-shell:client-portal-quote-detail",
                    ],
                    "permission_domain": "client_portal_quotes",
                    "permission_action": "view",
                },
                {
                    "label": "Contratos",
                    "url_name": "admin-shell:client-portal-contracts",
                    "match_names": [
                        "admin-shell:client-portal-contracts",
                        "admin-shell:client-portal-contract-detail",
                    ],
                    "permission_domain": "client_portal_contracts",
                    "permission_action": "view",
                },
                {
                    "label": "Solicitacoes",
                    "url_name": "admin-shell:client-portal-requests",
                    "match_names": [
                        "admin-shell:client-portal-requests",
                        "admin-shell:client-portal-request-create",
                        "admin-shell:client-portal-request-detail",
                    ],
                    "permission_domain": "client_portal_requests",
                    "permission_action": "view",
                },
            ],
        },
        {
            "label": "Conta",
            "items": [
                {
                    "label": "Meu Perfil",
                    "url_name": "admin-shell:client-portal-profile",
                    "match_names": ["admin-shell:client-portal-profile"],
                    "permission_domain": "client_portal_profile",
                    "permission_action": "view",
                },
            ],
        },
    ]
    permission_map = permission_map or {}
    filtered = []
    for section in navigation:
        items = filter_permissioned_items(section["items"], permission_map)
        if items:
            filtered.append({"label": section["label"], "items": items})
    for section in filtered:
        for item in section["items"]:
            item["is_active"] = current_url_name in item.get("match_names", [item.get("url_name")])
    return filtered


def get_client_portal_quick_actions():
    return [
        {
            "label": "Copiloto",
            "route_name": "admin-shell:client-portal-copilot",
            "permission_domain": "client_portal_dashboard",
            "permission_action": "view",
        },
        {
            "label": "Abrir chamado",
            "route_name": "admin-shell:client-portal-request-create",
            "permission_domain": "client_portal_requests",
            "permission_action": "create",
        },
        {
            "label": "Ver relatorios",
            "route_name": "admin-shell:client-portal-reports",
            "permission_domain": "client_portal_reports",
            "permission_action": "view",
        },
        {
            "label": "Preventivas",
            "route_name": "admin-shell:client-portal-preventives",
            "permission_domain": "client_portal_preventives",
            "permission_action": "view",
        },
        {
            "label": "Orcamentos",
            "route_name": "admin-shell:client-portal-quotes",
            "permission_domain": "client_portal_quotes",
            "permission_action": "view",
        },
        {
            "label": "Contratos",
            "route_name": "admin-shell:client-portal-contracts",
            "permission_domain": "client_portal_contracts",
            "permission_action": "view",
        },
    ]


def get_client_portal_user_payload(user):
    return {
        "name": user.display_name or user.full_name or user.email,
        "email": user.email,
        "initials": "".join(part[0] for part in (user.first_name, user.last_name) if part).upper()[:2] or "CL",
        "job_title": user.job_title or "Contato do cliente",
    }


def build_client_portal_context(request, tenant_context, permission_map):
    current_name = getattr(getattr(request, "resolver_match", None), "view_name", "")
    billing_context = BillingAccessService.get_company_billing_context(tenant_context.get("company"))
    alerts = []
    if billing_context["warning"]:
        alerts.append(
            {
                "tone": "warning",
                "title": "Assinatura em atencao",
                "description": billing_context["warning"],
            }
        )
    if tenant_context.get("site"):
        alerts.append(
            {
                "tone": "info",
                "title": "Contexto ativo por unidade",
                "description": f"Dados filtrados para {tenant_context['site'].name}.",
            }
        )
    return {
        "portal_navigation": get_client_portal_navigation(current_name, permission_map=permission_map),
        "portal_user": get_client_portal_user_payload(request.user),
        "portal_tenant_context": tenant_context,
        "portal_alerts": alerts,
        "portal_notifications": alerts,
        "portal_quick_actions": filter_permissioned_items(get_client_portal_quick_actions(), permission_map),
        "portal_billing_context": billing_context,
    }


def _apply_text_filters(queryset, *, term="", fields=None):
    if not term or not fields:
        return queryset
    query = Q()
    for field in fields:
        query |= Q(**{f"{field}__icontains": term})
    return queryset.filter(query)


def _scoped_queryset(model, request):
    return SmartSystemScopeService.scope_related_queryset(model, request)


def _portal_role_slugs(user, company=None):
    queryset = UserRoleAssignment.objects.filter(user=user, is_active=True).select_related("role")
    if company is not None:
        queryset = queryset.filter(
            Q(company=company) | Q(scope_type=UserRoleAssignment.ScopeType.GLOBAL)
        )
    return set(queryset.values_list("role__slug", flat=True))


def _request_queryset_for_user(request, tenant_context):
    queryset = _scoped_queryset(ClientPortalRequest, request).select_related(
        "company",
        "operational_site",
        "asset",
        "related_service_order",
        "requester",
    )
    role_slugs = _portal_role_slugs(request.user, tenant_context.get("company"))
    if role_slugs and role_slugs.issubset({"requester"}):
        queryset = queryset.filter(requester=request.user)
    return queryset


def _quote_queryset(request):
    return _scoped_queryset(ServiceQuote, request).select_related(
        "company",
        "operational_site",
        "work_order",
        "asset",
        "approved_by_user",
    ).prefetch_related("items", "items__stock_item")


def _contract_queryset(request):
    return _scoped_queryset(MaintenanceContract, request).select_related(
        "company",
        "client",
        "operational_site",
    ).prefetch_related("covered_assets", "covered_assets__asset")


def get_client_dashboard_context(request, tenant_context):
    assets = _scoped_queryset(Asset, request)
    work_orders = _scoped_queryset(ServiceOrder, request)
    preventives = _scoped_queryset(MaintenancePlan, request)
    failures = _scoped_queryset(FailureEvent, request)
    requests = _request_queryset_for_user(request, tenant_context)
    quotes = _quote_queryset(request)
    contracts = _contract_queryset(request)
    sites = _scoped_queryset(OperationalSite, request)
    reports = _map_portal_report_entries(get_report_history_entries(tenant_context=tenant_context))
    now = timezone.now()
    today = timezone.localdate()

    site_rows = []
    for site in sites[:6]:
        site_rows.append(
            {
                "name": site.name,
                "city": site.city or "-",
                "assets": assets.filter(operational_site=site).count(),
                "open_orders": work_orders.filter(
                    operational_site=site,
                    status__in=[ServiceOrder.Status.OPEN, ServiceOrder.Status.SCHEDULED, ServiceOrder.Status.IN_PROGRESS],
                ).count(),
                "due_preventives": preventives.filter(
                    operational_site=site,
                    next_due_date__isnull=False,
                    next_due_date__lte=today,
                ).count(),
            }
        )

    recent_orders = work_orders.select_related("asset", "operational_site").order_by("-opened_at")[:5]
    recent_requests = requests.order_by("-created_at")[:5]

    return {
        "dashboard_kpis": [
            {"label": "Ativos monitorados", "value": assets.count(), "meta": "ativos no contexto atual", "tone": "indigo"},
            {
                "label": "OS em aberto",
                "value": work_orders.filter(status__in=[ServiceOrder.Status.OPEN, ServiceOrder.Status.SCHEDULED]).count(),
                "meta": "demandas aguardando atendimento",
                "tone": "amber",
            },
            {
                "label": "OS em andamento",
                "value": work_orders.filter(status=ServiceOrder.Status.IN_PROGRESS).count(),
                "meta": "atendimentos em execucao",
                "tone": "sky",
            },
            {
                "label": "Preventivas do mes",
                "value": preventives.filter(next_due_date__month=today.month).count(),
                "meta": "agenda preventiva dentro do mes corrente",
                "tone": "emerald",
            },
            {"label": "Falhas recentes", "value": failures.filter(detected_at__gte=now - timedelta(days=30)).count(), "meta": "ultimos 30 dias", "tone": "red"},
            {"label": "Relatorios disponiveis", "value": len(reports), "meta": "documentos tecnicos no portal", "tone": "violet"},
            {"label": "Orcamentos pendentes", "value": quotes.filter(status=ServiceQuote.Status.SENT).count(), "meta": "aguardando aceite", "tone": "amber"},
            {"label": "Contratos ativos", "value": contracts.filter(status=MaintenanceContract.Status.ACTIVE).count(), "meta": "cobertura vigente", "tone": "indigo"},
            {"label": "Chamados abertos", "value": requests.filter(status__in=[ClientPortalRequest.Status.OPEN, ClientPortalRequest.Status.UNDER_REVIEW, ClientPortalRequest.Status.IN_PROGRESS]).count(), "meta": "solicitacoes em acompanhamento", "tone": "orange"},
            {"label": "Unidades monitoradas", "value": sites.count(), "meta": "sites no escopo autorizado", "tone": "teal"},
        ],
        "dashboard_recent_orders": [
            {
                "code": order.order_number,
                "title": order.title,
                "asset": order.asset.asset_tag if order.asset else "-",
                "site": order.operational_site.name,
                "status": order.get_status_display(),
                "opened_at": timezone.localtime(order.opened_at).strftime("%d/%m/%Y %H:%M"),
            }
            for order in recent_orders
        ],
        "dashboard_recent_reports": reports[:5],
        "dashboard_pending_quotes": list(quotes.filter(status=ServiceQuote.Status.SENT).order_by("-sent_at")[:5]),
        "dashboard_contracts": list(contracts.filter(status=MaintenanceContract.Status.ACTIVE).order_by("-created_at")[:5]),
        "dashboard_recent_requests": list(recent_requests),
        "dashboard_sites": site_rows,
        "page_actions": [
            {"label": "Abrir chamado", "route_name": "admin-shell:client-portal-request-create", "permission_domain": "client_portal_requests", "permission_action": "create"},
            {"label": "Ver ativos", "route_name": "admin-shell:client-portal-assets", "permission_domain": "client_portal_assets", "permission_action": "view"},
            {"label": "Relatorios", "route_name": "admin-shell:client-portal-reports", "permission_domain": "client_portal_reports", "permission_action": "view"},
            {"label": "Orcamentos", "route_name": "admin-shell:client-portal-quotes", "permission_domain": "client_portal_quotes", "permission_action": "view"},
            {"label": "Contratos", "route_name": "admin-shell:client-portal-contracts", "permission_domain": "client_portal_contracts", "permission_action": "view"},
        ],
    }


def get_client_asset_listing_context(request, filters, tenant_context):
    queryset = _scoped_queryset(Asset, request).select_related(
        "category",
        "operational_site",
        "operational_site__maintenance_client",
    )
    queryset = _apply_text_filters(queryset, term=filters.get("search", ""), fields=["asset_tag", "name", "manufacturer", "model"])
    if filters.get("category"):
        queryset = queryset.filter(category__name__icontains=filters["category"])
    if filters.get("status"):
        queryset = queryset.filter(status=filters["status"])
    if filters.get("site"):
        queryset = queryset.filter(operational_site__name__icontains=filters["site"])

    records = []
    for asset in queryset.order_by("operational_site__name", "asset_tag"):
        latest_order = asset.service_orders.order_by("-opened_at").first()
        next_plan = asset.maintenance_plans.filter(is_active=True).order_by("next_due_date").first()
        records.append(
            {
                "code": asset.asset_tag,
                "name": asset.name,
                "category": asset.category.name,
                "site": asset.operational_site.name,
                "status": asset.get_status_display(),
                "criticality": asset.get_criticality_display(),
                "last_maintenance": timezone.localdate(latest_order.completed_at).strftime("%d/%m/%Y") if latest_order and latest_order.completed_at else "-",
                "next_preventive": next_plan.next_due_date.strftime("%d/%m/%Y") if next_plan and next_plan.next_due_date else "-",
                "detail_url": f"/portal/assets/{asset.asset_tag}/",
            }
        )

    return {
        "asset_filters": filters,
        "asset_records": records,
        "asset_highlights": [
            {"label": "Ativos monitorados", "value": queryset.count(), "meta": "ativos visiveis no portal", "tone": "indigo"},
            {"label": "Criticos", "value": queryset.filter(criticality=Asset.Criticality.CRITICAL).count(), "meta": "ativos com criticidade maxima", "tone": "red"},
            {"label": "Em manutencao", "value": queryset.filter(status=Asset.Status.MAINTENANCE).count(), "meta": "ativos em manutencao ou indisponiveis", "tone": "amber"},
        ],
        "page_actions": [
            {"label": "Abrir chamado", "route_name": "admin-shell:client-portal-request-create", "permission_domain": "client_portal_requests", "permission_action": "create"},
            {"label": "Ordens de servico", "route_name": "admin-shell:client-portal-work-orders", "permission_domain": "client_portal_work_orders", "permission_action": "view"},
        ],
    }


def get_client_asset_detail_context(request, asset_code):
    asset = _scoped_queryset(Asset, request).select_related(
        "category",
        "operational_site",
        "operational_site__maintenance_client",
    ).filter(asset_tag=asset_code).first()
    if asset is None:
        return None
    recent_failures = list(asset.failure_events.order_by("-detected_at")[:4])
    recent_orders = list(asset.service_orders.order_by("-opened_at")[:4])
    next_plan = asset.maintenance_plans.filter(is_active=True).order_by("next_due_date").first()
    reports = _map_portal_report_entries(
        [
            item
            for item in get_report_history_entries(
                tenant_context={"company": asset.operational_site.maintenance_client.company, "site": asset.operational_site}
            )
            if item["reference_code"] == asset.asset_tag
        ]
    )
    return {
        "asset": asset,
        "next_plan": next_plan,
        "recent_failures": recent_failures,
        "recent_orders": recent_orders,
        "related_reports": reports,
        "page_actions": [
            {"label": "Abrir chamado", "route_name": "admin-shell:client-portal-request-create", "permission_domain": "client_portal_requests", "permission_action": "create"},
            {"label": "Ver OS", "route_name": "admin-shell:client-portal-work-orders", "permission_domain": "client_portal_work_orders", "permission_action": "view"},
            {"label": "Ver relatorios", "route_name": "admin-shell:client-portal-reports", "permission_domain": "client_portal_reports", "permission_action": "view"},
        ],
    }


def get_client_work_order_listing_context(request, filters):
    queryset = _scoped_queryset(ServiceOrder, request).select_related(
        "asset",
        "operational_site",
        "assigned_to",
    )
    queryset = _apply_text_filters(queryset, term=filters.get("search", ""), fields=["order_number", "title", "asset__asset_tag"])
    if filters.get("status"):
        queryset = queryset.filter(status=filters["status"])
    if filters.get("priority"):
        queryset = queryset.filter(priority=filters["priority"])
    if filters.get("site"):
        queryset = queryset.filter(operational_site__name__icontains=filters["site"])
    if filters.get("asset"):
        queryset = queryset.filter(asset__asset_tag__icontains=filters["asset"])

    records = list(queryset.order_by("-opened_at"))
    return {
        "work_order_filters": filters,
        "work_order_records": records,
        "work_order_kpis": [
            {"label": "OS abertas", "value": queryset.filter(status=ServiceOrder.Status.OPEN).count(), "meta": "ordens aguardando triagem", "tone": "amber"},
            {"label": "Em andamento", "value": queryset.filter(status=ServiceOrder.Status.IN_PROGRESS).count(), "meta": "atendimentos em execucao", "tone": "sky"},
            {"label": "Concluidas recentes", "value": queryset.filter(status=ServiceOrder.Status.COMPLETED).count(), "meta": "ordens dentro do contexto autorizado", "tone": "emerald"},
        ],
        "page_actions": [
            {"label": "Abrir chamado", "route_name": "admin-shell:client-portal-request-create", "permission_domain": "client_portal_requests", "permission_action": "create"},
            {"label": "Relatorios", "route_name": "admin-shell:client-portal-reports", "permission_domain": "client_portal_reports", "permission_action": "view"},
        ],
    }


def get_client_work_order_detail_context(request, order_code):
    order = _scoped_queryset(ServiceOrder, request).select_related(
        "client",
        "operational_site",
        "asset",
        "assigned_to",
        "maintenance_plan",
    ).filter(order_number=order_code).first()
    if order is None:
        return None
    reports = _map_portal_report_entries(
        [
            item
            for item in get_report_history_entries(
                tenant_context={"company": order.client.company, "site": order.operational_site}
            )
            if item["reference_code"] == order.order_number
        ]
    )
    quote = _quote_queryset(request).filter(work_order=order).order_by("-created_at").first()
    page_actions = [
        {"label": "Relatorio tecnico", "route_name": "admin-shell:client-portal-report-preview", "route_kwargs": {"report_type": "work-order", "reference_code": order.order_number}, "permission_domain": "client_portal_reports", "permission_action": "view"},
        {"label": "Abrir chamado", "route_name": "admin-shell:client-portal-request-create", "permission_domain": "client_portal_requests", "permission_action": "create"},
    ]
    if quote is not None:
        page_actions.insert(
            1,
            {"label": "Orcamento", "href": f"/portal/quotes/{quote.quote_number}/", "permission_domain": "client_portal_quotes", "permission_action": "view"},
        )
    return {
        "work_order": order,
        "attachments": list(order.attachments.order_by("-created_at")[:6]),
        "reports": reports,
        "related_quote": quote,
        "page_actions": page_actions,
    }


def get_client_preventive_listing_context(request, filters):
    queryset = _scoped_queryset(MaintenancePlan, request).select_related(
        "asset",
        "category",
        "operational_site",
        "checklist",
    )
    queryset = _apply_text_filters(queryset, term=filters.get("search", ""), fields=["name", "asset__asset_tag", "asset__name"])
    if filters.get("site"):
        queryset = queryset.filter(operational_site__name__icontains=filters["site"])
    if filters.get("status") == "overdue":
        queryset = queryset.filter(next_due_date__lt=timezone.localdate())
    records = list(queryset.order_by("next_due_date", "name"))
    return {
        "preventive_filters": filters,
        "preventive_records": records,
        "preventive_kpis": [
            {"label": "Planos ativos", "value": queryset.filter(is_active=True).count(), "meta": "cobertura preventiva do tenant", "tone": "indigo"},
            {"label": "Vencidas", "value": queryset.filter(next_due_date__lt=timezone.localdate()).count(), "meta": "execucoes fora da janela", "tone": "red"},
            {"label": "Com checklist", "value": queryset.filter(checklist__isnull=False).count(), "meta": "planos com rotina estruturada", "tone": "emerald"},
        ],
        "page_actions": [
            {"label": "Ver relatorios", "route_name": "admin-shell:client-portal-reports", "permission_domain": "client_portal_reports", "permission_action": "view"},
        ],
    }


def get_client_preventive_detail_context(request, public_id):
    plan = _scoped_queryset(MaintenancePlan, request).select_related(
        "asset",
        "operational_site",
        "category",
        "checklist",
    ).filter(public_id=public_id).first()
    if plan is None:
        return None
    related_orders = list(plan.service_orders.order_by("-opened_at")[:6])
    page_actions = [
        {"label": "Relatorios", "route_name": "admin-shell:client-portal-reports", "permission_domain": "client_portal_reports", "permission_action": "view"},
    ]
    if plan.asset:
        page_actions.append(
            {"label": "Ativo", "href": f"/portal/assets/{plan.asset.asset_tag}/", "permission_domain": "client_portal_assets", "permission_action": "view"}
        )
    return {
        "plan": plan,
        "related_orders": related_orders,
        "page_actions": page_actions,
    }


def get_client_report_listing_context(tenant_context):
    mapped_entries = _map_portal_report_entries(get_report_history_entries(tenant_context=tenant_context))
    return {
        "report_records": mapped_entries,
        "report_kpis": [
            {"label": "Documentos disponiveis", "value": len(mapped_entries), "meta": "relatorios e fichas tecnicas", "tone": "indigo"},
            {"label": "Com checklist", "value": sum(1 for entry in mapped_entries if entry["has_checklist"]), "meta": "rotinas tecnicas registradas", "tone": "emerald"},
            {"label": "Com materiais", "value": sum(1 for entry in mapped_entries if entry["has_materials"]), "meta": "intervencoes com pecas e insumos", "tone": "amber"},
        ],
        "page_actions": [],
    }


def get_client_report_preview(report_type, reference_code, tenant_context):
    return get_report_preview_context(report_type, reference_code, tenant_context=tenant_context)


def get_client_quote_listing_context(request):
    queryset = _quote_queryset(request).order_by("-created_at")
    return {
        "quote_records": list(queryset),
        "quote_kpis": [
            {"label": "Pendentes", "value": queryset.filter(status=ServiceQuote.Status.SENT).count(), "meta": "aguardando aprovacao", "tone": "amber"},
            {"label": "Aprovados", "value": queryset.filter(status=ServiceQuote.Status.APPROVED).count(), "meta": "liberados para execucao", "tone": "emerald"},
            {"label": "Rejeitados", "value": queryset.filter(status=ServiceQuote.Status.REJECTED).count(), "meta": "retidos ou cancelados", "tone": "rose"},
        ],
        "page_actions": [],
    }


def get_client_quote_detail_context(request, quote_number):
    quote = _quote_queryset(request).filter(quote_number=quote_number).first()
    if quote is None:
        return None
    return {
        "quote": quote,
        "quote_items": list(quote.items.all()),
        "page_actions": [
            {"label": "Aprovar", "href": f"/portal/quotes/{quote.quote_number}/approve/", "permission_domain": "client_portal_quotes", "permission_action": "approve"},
            {"label": "Rejeitar", "href": f"/portal/quotes/{quote.quote_number}/reject/", "permission_domain": "client_portal_quotes", "permission_action": "reject"},
            {"label": "Abrir OS", "route_name": "admin-shell:client-portal-work-order-detail", "route_kwargs": {"order_code": quote.work_order.order_number}, "permission_domain": "client_portal_work_orders", "permission_action": "view"},
        ],
    }


def get_client_contract_listing_context(request):
    queryset = _contract_queryset(request).order_by("-created_at")
    return {
        "contract_records": list(queryset),
        "contract_kpis": [
            {"label": "Contratos ativos", "value": queryset.filter(status=MaintenanceContract.Status.ACTIVE).count(), "meta": "cobertura vigente", "tone": "emerald"},
            {"label": "Ativos cobertos", "value": sum(contract.covered_assets.count() for contract in queryset), "meta": "escopo contratual", "tone": "sky"},
            {"label": "Com vencimento", "value": queryset.exclude(end_date__isnull=True).count(), "meta": "acompanhar renovacao", "tone": "amber"},
        ],
        "page_actions": [],
    }


def get_client_contract_detail_context(request, contract_number):
    contract = _contract_queryset(request).filter(contract_number=contract_number).first()
    if contract is None:
        return None
    return {
        "contract": contract,
        "contract_assets": list(contract.covered_assets.select_related("asset", "asset__category", "asset__operational_site").all()),
        "contract_orders": list(
            _scoped_queryset(ServiceOrder, request)
            .filter(maintenance_contract=contract)
            .select_related("asset", "operational_site")
            .order_by("-opened_at")[:8]
        ),
        "page_actions": [
            {"label": "Ver preventivas", "route_name": "admin-shell:client-portal-preventives", "permission_domain": "client_portal_preventives", "permission_action": "view"},
            {"label": "Ver ativos", "route_name": "admin-shell:client-portal-assets", "permission_domain": "client_portal_assets", "permission_action": "view"},
        ],
    }


def get_client_request_listing_context(request, filters, tenant_context):
    queryset = _request_queryset_for_user(request, tenant_context)
    queryset = _apply_text_filters(queryset, term=filters.get("search", ""), fields=["protocol_number", "title", "description"])
    if filters.get("status"):
        queryset = queryset.filter(status=filters["status"])
    if filters.get("priority"):
        queryset = queryset.filter(priority=filters["priority"])
    if filters.get("site"):
        queryset = queryset.filter(operational_site__name__icontains=filters["site"])
    return {
        "request_filters": filters,
        "request_records": list(queryset.order_by("-created_at")),
        "request_kpis": [
            {"label": "Solicitacoes abertas", "value": queryset.filter(status=ClientPortalRequest.Status.OPEN).count(), "meta": "protocolo aguardando triagem", "tone": "amber"},
            {"label": "Em tratamento", "value": queryset.filter(status=ClientPortalRequest.Status.IN_PROGRESS).count(), "meta": "solicitacoes em andamento", "tone": "sky"},
            {"label": "Resolvidas", "value": queryset.filter(status=ClientPortalRequest.Status.RESOLVED).count(), "meta": "historico concluido", "tone": "emerald"},
        ],
        "page_actions": [
            {"label": "Nova solicitacao", "route_name": "admin-shell:client-portal-request-create", "permission_domain": "client_portal_requests", "permission_action": "create"},
        ],
    }


def get_client_request_detail_context(request, protocol_number, tenant_context):
    client_request = _request_queryset_for_user(request, tenant_context).filter(protocol_number=protocol_number).first()
    if client_request is None:
        return None
    timeline = [
        {
            "label": "Solicitacao aberta",
            "timestamp": timezone.localtime(client_request.created_at).strftime("%d/%m/%Y %H:%M"),
            "description": client_request.description,
        },
        {
            "label": "Ultima atualizacao",
            "timestamp": timezone.localtime(client_request.last_customer_update_at).strftime("%d/%m/%Y %H:%M"),
            "description": client_request.resolution_summary or "Aguardando proxima atualizacao operacional.",
        },
    ]
    if client_request.related_service_order_id:
        timeline.append(
            {
                "label": "OS vinculada",
                "timestamp": timezone.localtime(client_request.related_service_order.created_at).strftime("%d/%m/%Y %H:%M"),
                "description": f"Ordem {client_request.related_service_order.order_number} vinculada ao protocolo.",
            }
        )
    return {
        "client_request": client_request,
        "request_timeline": timeline,
        "page_actions": [
            {"label": "Voltar para solicitacoes", "route_name": "admin-shell:client-portal-requests", "permission_domain": "client_portal_requests", "permission_action": "view"},
            {"label": "Abrir novo chamado", "route_name": "admin-shell:client-portal-request-create", "permission_domain": "client_portal_requests", "permission_action": "create"},
        ],
    }


def create_client_portal_request(form, *, user, tenant_context):
    company = tenant_context.get("company")
    next_sequence = ClientPortalRequest.objects.filter(company=company).count() + 1
    protocol_number = f"PCR-{timezone.localdate().strftime('%Y%m%d')}-{next_sequence:04d}"
    portal_request = form.save(commit=False)
    portal_request.company = company
    portal_request.requester = user
    portal_request.protocol_number = protocol_number
    portal_request.last_customer_update_at = timezone.now()
    portal_request.save()
    return portal_request


def get_client_site_listing_context(request):
    sites = _scoped_queryset(OperationalSite, request).select_related("maintenance_client", "maintenance_client__company")
    site_cards = []
    for site in sites.order_by("name"):
        asset_count = Asset.objects.filter(operational_site=site).count()
        open_orders = ServiceOrder.objects.filter(
            operational_site=site,
            status__in=[ServiceOrder.Status.OPEN, ServiceOrder.Status.SCHEDULED, ServiceOrder.Status.IN_PROGRESS],
        ).count()
        due_preventives = MaintenancePlan.objects.filter(
            operational_site=site,
            next_due_date__isnull=False,
            next_due_date__lte=timezone.localdate(),
        ).count()
        site_cards.append(
            {
                "site": site,
                "asset_count": asset_count,
                "open_orders": open_orders,
                "due_preventives": due_preventives,
            }
        )
    return {"site_cards": site_cards}


def get_client_profile_context(user, tenant_context):
    company = tenant_context.get("company")
    billing_context = BillingAccessService.get_company_billing_context(company)
    roles = sorted(_portal_role_slugs(user, company))
    return {
        "profile_user": user,
        "profile_roles": roles,
        "profile_company": company,
        "profile_site": tenant_context.get("site"),
        "profile_billing": billing_context,
    }


def generate_client_report_pdf(report_type, reference_code, tenant_context):
    return generate_report_pdf(report_type, reference_code, tenant_context=tenant_context)


def _map_portal_report_entries(entries):
    mapped_entries = []
    for entry in entries:
        report_type = _resolve_report_type_slug(entry["report_code"], entry["reference_code"])
        mapped = dict(entry)
        mapped["report_type_slug"] = report_type
        mapped["portal_preview_url"] = f"/portal/reports/{report_type}/{entry['reference_code']}/"
        mapped["portal_download_url"] = f"/portal/reports/{report_type}/{entry['reference_code']}/download/"
        mapped_entries.append(mapped)
    return mapped_entries


def _resolve_report_type_slug(report_code, reference_code):
    if report_code.startswith("RT-OS"):
        return "work-order"
    if report_code.startswith("RT-COR"):
        return "corrective"
    if report_code.startswith("RT-PM"):
        return "preventive"
    if report_code.startswith("RT-FE"):
        return "failure"
    if report_code.startswith("FT-ATV") or reference_code.startswith(("AST-", "CHILLER", "CAMARA", "ESTEIRA", "HVAC", "COMPRESSOR", "BIKE")):
        return "asset-summary"
    return "work-order"
