from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.ai_agents_center.models import (
    AgentRecommendation,
    ClientPortalCopilotConfiguration,
    ClientPortalCopilotMessage,
    ClientPortalCopilotSession,
)
from apps.admin_shell.services.client_portal import (
    get_client_asset_detail_context,
    get_client_contract_detail_context,
    get_client_dashboard_context,
    get_client_preventive_detail_context,
    get_client_quote_detail_context,
    get_client_report_preview,
    get_client_request_detail_context,
    get_client_work_order_detail_context,
)
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import Asset, MaintenanceContract, MaintenancePlan, OperationalSite, ServiceOrder, ServiceQuote
from apps.smart_system.services.tenant_scope import SmartSystemScopeService
from shared_kernel.observability.context import get_request_id


@dataclass(frozen=True)
class PortalIntent:
    key: str
    response_type: str


class ClientPortalSafeResponsePolicy:
    BLOCKED_TERMS = (
        "margem",
        "lucro",
        "prejuizo",
        "rentabilidade",
        "custo",
        "interno",
        "comite",
        "pricing",
        "repricing",
        "profitability",
    )

    SAFE_RECOMMENDATION_TYPES = {
        AgentRecommendation.RecommendationType.PREVENTIVE_REVIEW,
        AgentRecommendation.RecommendationType.EXTRAORDINARY_INSPECTION,
        AgentRecommendation.RecommendationType.FAILURE_PATTERN_ALERT,
        AgentRecommendation.RecommendationType.RELIABILITY_ATTENTION,
        AgentRecommendation.RecommendationType.CRITICAL_ASSET_WATCH,
        AgentRecommendation.RecommendationType.ANOMALY_FAILURE_SPIKE,
        AgentRecommendation.RecommendationType.ANOMALY_SITE_RISK_ALERT,
        AgentRecommendation.RecommendationType.ANOMALY_SLA_DROP,
    }

    @classmethod
    def is_safe_text(cls, text: str) -> bool:
        lowered = (text or "").lower()
        return not any(term in lowered for term in cls.BLOCKED_TERMS)

    @classmethod
    def sanitize_text(cls, text: str, *, fallback: str = "") -> str:
        return text if cls.is_safe_text(text) else fallback

    @classmethod
    def sanitize_recommendation(cls, recommendation: AgentRecommendation) -> dict | None:
        if recommendation.recommendation_type not in cls.SAFE_RECOMMENDATION_TYPES:
            return None
        summary = cls.sanitize_text(recommendation.summary)
        explanation = cls.sanitize_text(recommendation.explanation)
        if not summary:
            return None
        return {
            "agent": recommendation.agent_run.agent.name,
            "title": recommendation.title,
            "summary": summary,
            "explanation": explanation,
            "severity": recommendation.severity,
            "priority": recommendation.priority,
            "requires_human_approval": recommendation.requires_human_approval,
        }


class ClientPortalCopilotService:
    DEFAULT_SUGGESTIONS = [
        "Como esta a unidade hoje?",
        "Tem alguma OS atrasada?",
        "O que mudou desde a semana passada?",
        "Quais documentos eu posso baixar agora?",
        "O que esta pendente da minha aprovacao?",
        "Explique este relatorio de forma simples.",
    ]

    INTENT_KEYWORDS = {
        "report_explanation": ["relatorio", "documento", "laudo", "quer dizer"],
        "quote_explanation": ["orcamento", "aprovar", "rejeitar", "peca", "servico"],
        "work_order_status": ["os", "ordem", "atendimento", "status da os", "servico"],
        "preventive_status": ["preventiva", "programada", "realizada", "atrasada"],
        "asset_summary": ["ativo", "equipamento", "camera", "chiller", "historico"],
        "pending_actions": ["pendente", "aprovacao", "proximo passo", "proximos passos", "atrasada"],
        "comparison": ["mudou", "comparado", "comparar", "semana passada", "desde a semana passada"],
        "site_summary": ["unidade", "site", "hoje", "situacao", "como esta"],
    }

    @classmethod
    def get_configuration(cls, *, company=None):
        configuration = None
        if company is not None:
            configuration = ClientPortalCopilotConfiguration.objects.filter(company=company).first()
        if configuration is None:
            configuration = ClientPortalCopilotConfiguration.objects.filter(company__isnull=True).first()
        return configuration

    @classmethod
    def get_or_create_session(cls, *, user, tenant_context, session_public_id=None):
        company = tenant_context.get("company")
        site = tenant_context.get("site")
        queryset = ClientPortalCopilotSession.objects.filter(user=user, company=company, site=site)
        if session_public_id:
            session = queryset.filter(public_id=session_public_id).first()
            if session is not None:
                return session
        session = queryset.order_by("-last_activity_at").first()
        if session is not None:
            return session
        return ClientPortalCopilotSession.objects.create(
            user=user,
            company=company,
            site=site,
            status=ClientPortalCopilotSession.Status.ACTIVE,
            title="Copilot do cliente",
            current_context={},
        )

    @classmethod
    def classify_intent(cls, query: str) -> PortalIntent:
        normalized = (query or "").strip().lower()
        if not normalized:
            return PortalIntent("site_summary", "operational_summary")
        for intent, keywords in cls.INTENT_KEYWORDS.items():
            if any(keyword in normalized for keyword in keywords):
                response_type = "status_explanation"
                if intent == "report_explanation":
                    response_type = "report_explanation"
                elif intent == "quote_explanation":
                    response_type = "quote_explanation"
                elif intent == "comparison":
                    response_type = "period_comparison"
                elif intent in {"site_summary", "asset_summary"}:
                    response_type = "operational_summary"
                elif intent == "pending_actions":
                    response_type = "pending_actions"
                return PortalIntent(intent, response_type)
        return PortalIntent("site_summary", "operational_summary")

    @classmethod
    def _contains(cls, haystack: str, needles: list[str]) -> bool:
        normalized = haystack.lower()
        return any(needle and needle.lower() in normalized for needle in needles)

    @classmethod
    def _resolve_entities(cls, *, request, tenant_context, query: str, context_seed: dict | None, session_context: dict | None):
        context_seed = context_seed or {}
        session_context = session_context or {}
        resolved = {}
        merged = {}
        merged.update(session_context)
        merged.update(context_seed)

        asset_code = merged.get("asset_code") or merged.get("asset")
        order_code = merged.get("work_order_code") or merged.get("work_order")
        quote_number = merged.get("quote_number") or merged.get("quote")
        contract_number = merged.get("contract_number") or merged.get("contract")
        report_type = merged.get("report_type")
        report_reference = merged.get("report_reference") or merged.get("reference_code")
        preventive_public_id = merged.get("preventive_public_id") or merged.get("preventive")
        protocol_number = merged.get("protocol_number") or merged.get("request")
        site_code = merged.get("site_code") or merged.get("site")

        if asset_code:
            resolved["asset"] = get_client_asset_detail_context(request, asset_code)
        if order_code:
            resolved["work_order"] = get_client_work_order_detail_context(request, order_code)
        if quote_number:
            resolved["quote"] = get_client_quote_detail_context(request, quote_number)
        if contract_number:
            resolved["contract"] = get_client_contract_detail_context(request, contract_number)
        if preventive_public_id:
            resolved["preventive"] = get_client_preventive_detail_context(request, preventive_public_id)
        if protocol_number:
            resolved["request"] = get_client_request_detail_context(request, protocol_number, tenant_context)
        if report_type and report_reference:
            resolved["report"] = get_client_report_preview(report_type, report_reference, tenant_context)

        site_queryset = SmartSystemScopeService.scope_related_queryset(OperationalSite, request).filter(
            maintenance_client__company=tenant_context.get("company")
        )
        if tenant_context.get("site") is not None:
            site_queryset = site_queryset.filter(id=tenant_context["site"].id)
        if site_code:
            resolved["site"] = site_queryset.filter(code__iexact=site_code).first() or site_queryset.filter(name__icontains=site_code).first()

        normalized = (query or "").lower()
        if not resolved.get("site"):
            for site in site_queryset.order_by("name")[:20]:
                if cls._contains(normalized, [site.name, site.code]):
                    resolved["site"] = site
                    break

        if not resolved.get("asset"):
            for asset in SmartSystemScopeService.scope_related_queryset(Asset, request).filter(
                operational_site__in=site_queryset
            ).select_related("operational_site")[:30]:
                if cls._contains(normalized, [asset.asset_tag, asset.name]):
                    resolved["asset"] = get_client_asset_detail_context(request, asset.asset_tag)
                    break

        if not resolved.get("work_order"):
            for order in SmartSystemScopeService.scope_related_queryset(ServiceOrder, request).filter(
                operational_site__in=site_queryset
            ).select_related("asset", "operational_site")[:30]:
                if cls._contains(normalized, [order.order_number, order.title]):
                    resolved["work_order"] = get_client_work_order_detail_context(request, order.order_number)
                    break

        if not resolved.get("quote"):
            for quote in SmartSystemScopeService.scope_related_queryset(ServiceQuote, request).filter(
                company=tenant_context.get("company")
            ).select_related("work_order", "asset", "operational_site")[:20]:
                if cls._contains(normalized, [quote.quote_number]):
                    resolved["quote"] = get_client_quote_detail_context(request, quote.quote_number)
                    break

        if not resolved.get("contract"):
            for contract in SmartSystemScopeService.scope_related_queryset(MaintenanceContract, request).filter(
                company=tenant_context.get("company")
            ).select_related("operational_site")[:20]:
                if cls._contains(normalized, [contract.contract_number, getattr(contract.operational_site, "name", "")]):
                    resolved["contract"] = get_client_contract_detail_context(request, contract.contract_number)
                    break

        if not resolved.get("preventive"):
            for plan in SmartSystemScopeService.scope_related_queryset(MaintenancePlan, request).filter(
                company=tenant_context.get("company")
            ).select_related("asset", "operational_site")[:20]:
                if cls._contains(normalized, [plan.name, getattr(plan.asset, "asset_tag", ""), getattr(plan.asset, "name", "")]):
                    resolved["preventive"] = get_client_preventive_detail_context(request, str(plan.public_id))
                    break

        return resolved

    @classmethod
    def _safe_recommendations(cls, *, company, site=None):
        queryset = AgentRecommendation.objects.select_related("agent_run", "agent_run__agent").filter(company=company).order_by("-created_at")
        if site is not None:
            queryset = queryset.filter(site=site)
        safe = []
        for recommendation in queryset[:15]:
            sanitized = ClientPortalSafeResponsePolicy.sanitize_recommendation(recommendation)
            if sanitized:
                safe.append(sanitized)
        return safe[:4]

    @classmethod
    def _filter_actions(cls, actions: list[dict], permission_map: dict | None):
        permission_map = permission_map or {}
        filtered = []
        for action in actions:
            domain = action.get("permission_domain")
            permission_action = action.get("permission_action", "view")
            if domain and not permission_map.get(f"{domain}.{permission_action}", False):
                continue
            filtered.append(action)
        return filtered

    @classmethod
    def _dashboard_cards(cls, request, tenant_context):
        dashboard = get_client_dashboard_context(request, tenant_context)
        return dashboard["dashboard_kpis"][:4]

    @classmethod
    def _site_summary_response(cls, *, request, tenant_context, resolved, permission_map):
        dashboard = get_client_dashboard_context(request, tenant_context)
        site = resolved.get("site") or tenant_context.get("site")
        summary = (
            f"A unidade {site.name} esta com {next((row['open_orders'] for row in dashboard['dashboard_sites'] if row['name'] == site.name), 0)} OS abertas"
            if site is not None
            else "Resumo da operacao nas unidades autorizadas."
        )
        bullets = [
            f"{item['label']}: {item['value']} ({item['meta']})"
            for item in dashboard["dashboard_kpis"][:4]
        ]
        actions = cls._filter_actions(
            [
                {"label": "Ver ativos", "href": reverse("admin-shell:client-portal-assets"), "permission_domain": "client_portal_assets", "permission_action": "view"},
                {"label": "Ver OS", "href": reverse("admin-shell:client-portal-work-orders"), "permission_domain": "client_portal_work_orders", "permission_action": "view"},
                {"label": "Ver preventivas", "href": reverse("admin-shell:client-portal-preventives"), "permission_domain": "client_portal_preventives", "permission_action": "view"},
            ],
            permission_map,
        )
        return {
            "response_type": "operational_summary",
            "summary": summary,
            "bullets": bullets,
            "cards": dashboard["dashboard_kpis"][:6],
            "safe_recommendations": cls._safe_recommendations(company=tenant_context.get("company"), site=site),
            "actions": actions,
        }

    @classmethod
    def _asset_response(cls, *, asset_payload, permission_map):
        asset = asset_payload["asset"]
        failures = asset_payload["recent_failures"]
        orders = asset_payload["recent_orders"]
        next_plan = asset_payload["next_plan"]
        bullets = [
            f"Ultimas falhas registradas: {len(failures)} evento(s) recente(s).",
            f"Ultimas intervencoes: {len(orders)} ordem(ns) de servico no historico visivel.",
            (
                f"Proxima preventiva prevista para {next_plan.next_due_date:%d/%m/%Y}."
                if next_plan and next_plan.next_due_date
                else "Nao ha preventiva futura publicada no contexto atual."
            ),
        ]
        actions = cls._filter_actions(
            [
                {"label": "Abrir ativo", "href": reverse("admin-shell:client-portal-asset-detail", kwargs={"asset_code": asset.asset_tag}), "permission_domain": "client_portal_assets", "permission_action": "view"},
                {"label": "Ver OS do portal", "href": reverse("admin-shell:client-portal-work-orders"), "permission_domain": "client_portal_work_orders", "permission_action": "view"},
                {"label": "Ver relatorios", "href": reverse("admin-shell:client-portal-reports"), "permission_domain": "client_portal_reports", "permission_action": "view"},
            ],
            permission_map,
        )
        return {
            "response_type": "asset_view",
            "summary": f"{asset.asset_tag} - {asset.name} esta em {asset.get_status_display().lower()} na unidade {asset.operational_site.name}.",
            "bullets": bullets,
            "cards": [
                {"label": "Ativo", "value": asset.asset_tag, "meta": asset.name},
                {"label": "Criticidade", "value": asset.get_criticality_display(), "meta": asset.category.name},
                {"label": "Unidade", "value": asset.operational_site.name, "meta": asset.operational_site.code},
            ],
            "actions": actions,
        }

    @classmethod
    def _work_order_response(cls, *, payload, permission_map):
        order = payload["work_order"]
        bullets = [
            f"Status atual: {order.get_status_display()}.",
            f"Ativo relacionado: {order.asset.asset_tag if order.asset else '-'} - {order.asset.name if order.asset else 'Sem ativo'}.",
            f"Proximo passo esperado: {'encerramento tecnico' if order.status == ServiceOrder.Status.IN_PROGRESS else 'atendimento e atualizacao operacional'}.",
        ]
        if order.final_observations:
            bullets.append(f"Observacao publicada: {order.final_observations}.")
        actions = cls._filter_actions(
            [
                {"label": "Abrir detalhes da OS", "href": reverse("admin-shell:client-portal-work-order-detail", kwargs={"order_code": order.order_number}), "permission_domain": "client_portal_work_orders", "permission_action": "view"},
                {"label": "Ver relatorio tecnico", "href": reverse("admin-shell:client-portal-report-preview", kwargs={"report_type": "work-order", "reference_code": order.order_number}), "permission_domain": "client_portal_reports", "permission_action": "view"},
            ],
            permission_map,
        )
        return {
            "response_type": "status_explanation",
            "summary": f"A OS {order.order_number} esta {order.get_status_display().lower()} na unidade {order.operational_site.name}.",
            "bullets": bullets,
            "cards": [
                {"label": "OS", "value": order.order_number, "meta": order.title},
                {"label": "Status", "value": order.get_status_display(), "meta": order.get_priority_display()},
                {"label": "Unidade", "value": order.operational_site.name, "meta": order.opened_at.strftime('%d/%m/%Y %H:%M') if order.opened_at else "-"},
            ],
            "actions": actions,
        }

    @classmethod
    def _preventive_response(cls, *, payload, permission_map):
        plan = payload["plan"]
        actions = cls._filter_actions(
            [
                {"label": "Abrir preventiva", "href": reverse("admin-shell:client-portal-preventive-detail", kwargs={"public_id": plan.public_id}), "permission_domain": "client_portal_preventives", "permission_action": "view"},
                {"label": "Ver relatorios", "href": reverse("admin-shell:client-portal-reports"), "permission_domain": "client_portal_reports", "permission_action": "view"},
            ],
            permission_map,
        )
        return {
            "response_type": "status_explanation",
            "summary": f"A preventiva {plan.name} esta {'atrasada' if plan.next_due_date and plan.next_due_date < timezone.localdate() else 'programada'} para {plan.asset.asset_tag if plan.asset else 'o ativo vinculado'}.",
            "bullets": [
                f"Periodicidade: {plan.frequency_value} {plan.get_frequency_type_display().lower()}.",
                f"Proxima execucao prevista: {plan.next_due_date:%d/%m/%Y}." if plan.next_due_date else "Sem data futura publicada.",
                f"Checklist vinculado: {plan.checklist.name}." if plan.checklist else "Sem checklist publicado no portal.",
            ],
            "cards": [
                {"label": "Preventiva", "value": plan.name, "meta": plan.asset.asset_tag if plan.asset else "-"},
                {"label": "Unidade", "value": plan.operational_site.name, "meta": plan.category.name if plan.category else "-"},
            ],
            "actions": actions,
        }

    @classmethod
    def _report_response(cls, *, payload, permission_map):
        report = payload["report"]
        section_titles = [section["title"] for section in report.get("sections", [])[:4]]
        preview_href = reverse(
            "admin-shell:client-portal-report-preview",
            kwargs={"report_type": report["report_type"], "reference_code": report["reference_code"]},
        )
        download_href = reverse(
            "admin-shell:client-portal-report-download",
            kwargs={"report_type": report["report_type"], "reference_code": report["reference_code"]},
        )
        actions = cls._filter_actions(
            [
                {"label": "Abrir relatorio", "href": preview_href, "permission_domain": "client_portal_reports", "permission_action": "view"},
                {"label": "Baixar documento", "href": download_href, "permission_domain": "client_portal_reports", "permission_action": "export"},
            ],
            permission_map,
        )
        return {
            "response_type": "report_explanation",
            "summary": f"{report['document_type']} sobre {report['subject_title']} em linguagem mais simples.",
            "bullets": [
                f"Documento: {report['report_code']}.",
                f"Foco principal: {report['subject_subtitle']}.",
                f"O relatorio traz secoes como: {', '.join(section_titles)}." if section_titles else "O relatorio resume o atendimento e seus desdobramentos.",
                "Use o documento para acompanhar o que foi identificado, executado e o que ainda pode depender de aprovacao.",
            ],
            "cards": [
                {"label": "Relatorio", "value": report["report_code"], "meta": report["document_type"]},
                {"label": "Referencia", "value": report["reference_code"], "meta": report["subject_title"]},
            ],
            "actions": actions,
        }

    @classmethod
    def _quote_response(cls, *, payload, permission_map):
        quote = payload["quote"]
        actions = cls._filter_actions(
            [
                {"label": "Abrir orcamento", "href": reverse("admin-shell:client-portal-quote-detail", kwargs={"quote_number": quote.quote_number}), "permission_domain": "client_portal_quotes", "permission_action": "view"},
                {"label": "Aprovar orcamento", "href": reverse("admin-shell:client-portal-quote-detail", kwargs={"quote_number": quote.quote_number}), "permission_domain": "client_portal_quotes", "permission_action": "approve"},
                {"label": "Ver OS vinculada", "href": reverse("admin-shell:client-portal-work-order-detail", kwargs={"order_code": quote.work_order.order_number}), "permission_domain": "client_portal_work_orders", "permission_action": "view"},
            ],
            permission_map,
        )
        next_step = {
            ServiceQuote.Status.SENT: "aguarda sua aprovacao ou rejeicao",
            ServiceQuote.Status.APPROVED: "ja foi aprovado e pode seguir para execucao",
            ServiceQuote.Status.REJECTED: "foi rejeitado e nao sera executado sem nova tratativa",
        }.get(quote.status, "segue o fluxo normal do portal")
        return {
            "response_type": "quote_explanation",
            "summary": f"O orcamento {quote.quote_number} foi gerado para a OS {quote.work_order.order_number} e {next_step}.",
            "bullets": [
                f"Total de pecas: R$ {quote.total_parts}.",
                f"Total de servico: R$ {quote.total_labor}.",
                f"Total geral: R$ {quote.total_value}.",
                quote.customer_message or "A mensagem ao cliente usa o motivo publicado no proprio orcamento.",
            ],
            "cards": [
                {"label": "Orcamento", "value": quote.quote_number, "meta": quote.get_status_display()},
                {"label": "OS", "value": quote.work_order.order_number, "meta": quote.asset.asset_tag if quote.asset else "-"},
            ],
            "actions": actions,
        }

    @classmethod
    def _contract_response(cls, *, payload, permission_map):
        contract = payload["contract"]
        return {
            "response_type": "status_explanation",
            "summary": f"O contrato {contract.contract_number} esta {contract.get_status_display().lower()} para {contract.operational_site.name if contract.operational_site else 'o escopo contratado'}.",
            "bullets": [
                f"Inicio de vigencia: {contract.start_date:%d/%m/%Y}." if contract.start_date else "Inicio de vigencia nao informado.",
                f"Fim de vigencia: {contract.end_date:%d/%m/%Y}." if contract.end_date else "Sem data final publicada.",
                f"Ativos cobertos visiveis: {len(payload['contract_assets'])}.",
            ],
            "cards": [
                {"label": "Contrato", "value": contract.contract_number, "meta": contract.get_status_display()},
                {"label": "Cobertura", "value": len(payload['contract_assets']), "meta": "ativos visiveis"},
            ],
            "actions": cls._filter_actions(
                [
                    {"label": "Abrir contrato", "href": reverse("admin-shell:client-portal-contract-detail", kwargs={"contract_number": contract.contract_number}), "permission_domain": "client_portal_contracts", "permission_action": "view"},
                    {"label": "Ver preventivas", "href": reverse("admin-shell:client-portal-preventives"), "permission_domain": "client_portal_preventives", "permission_action": "view"},
                ],
                permission_map,
            ),
        }

    @classmethod
    def _pending_response(cls, *, request, tenant_context, permission_map):
        dashboard = get_client_dashboard_context(request, tenant_context)
        pending_quotes = dashboard["dashboard_pending_quotes"][:3]
        bullets = []
        for quote in pending_quotes:
            bullets.append(f"Orcamento {quote.quote_number} aguardando decisao para a OS {quote.work_order.order_number}.")
        if not bullets:
            bullets.append("Nao ha orcamentos pendentes no escopo atual.")
        if dashboard["dashboard_recent_requests"]:
            recent_request = dashboard["dashboard_recent_requests"][0]
            bullets.append(f"Solicitacao mais recente: {recent_request.protocol_number} em {recent_request.get_status_display().lower()}.")
        return {
            "response_type": "pending_actions",
            "summary": "Principais pendencias e proximos passos visiveis no portal.",
            "bullets": bullets,
            "cards": dashboard["dashboard_kpis"][6:10],
            "actions": cls._filter_actions(
                [
                    {"label": "Ver orcamentos pendentes", "href": reverse("admin-shell:client-portal-quotes"), "permission_domain": "client_portal_quotes", "permission_action": "view"},
                    {"label": "Abrir solicitacoes", "href": reverse("admin-shell:client-portal-requests"), "permission_domain": "client_portal_requests", "permission_action": "view"},
                    {"label": "Ver preventivas", "href": reverse("admin-shell:client-portal-preventives"), "permission_domain": "client_portal_preventives", "permission_action": "view"},
                ],
                permission_map,
            ),
        }

    @classmethod
    def _comparison_response(cls, *, request, tenant_context, permission_map):
        today = timezone.localdate()
        current_start = today - timedelta(days=6)
        comparison_end = current_start - timedelta(days=1)
        comparison_start = comparison_end - timedelta(days=6)
        company = tenant_context.get("company")
        site = tenant_context.get("site")
        order_queryset = SmartSystemScopeService.scope_related_queryset(ServiceOrder, request).filter(client__company=company)
        plan_queryset = SmartSystemScopeService.scope_related_queryset(MaintenancePlan, request).filter(company=company)
        if site is not None:
            order_queryset = order_queryset.filter(operational_site=site)
            plan_queryset = plan_queryset.filter(operational_site=site)
        current_orders = order_queryset.filter(opened_at__date__gte=current_start, opened_at__date__lte=today).count()
        previous_orders = order_queryset.filter(opened_at__date__gte=comparison_start, opened_at__date__lte=comparison_end).count()
        current_due = plan_queryset.filter(next_due_date__gte=current_start, next_due_date__lte=today).count()
        previous_due = plan_queryset.filter(next_due_date__gte=comparison_start, next_due_date__lte=comparison_end).count()
        return {
            "response_type": "period_comparison",
            "summary": "Comparacao simples entre os ultimos 7 dias e os 7 dias anteriores no seu escopo.",
            "bullets": [
                f"OS abertas no periodo atual: {current_orders} (periodo anterior: {previous_orders}).",
                f"Preventivas previstas no periodo atual: {current_due} (periodo anterior: {previous_due}).",
                "Use essa leitura para ver se houve concentracao maior de demanda ou manutencoes previstas.",
            ],
            "cards": [
                {"label": "OS 7 dias", "value": current_orders, "meta": f"antes: {previous_orders}"},
                {"label": "Preventivas 7 dias", "value": current_due, "meta": f"antes: {previous_due}"},
            ],
            "actions": cls._filter_actions(
                [
                    {"label": "Ver OS", "href": reverse("admin-shell:client-portal-work-orders"), "permission_domain": "client_portal_work_orders", "permission_action": "view"},
                    {"label": "Ver preventivas", "href": reverse("admin-shell:client-portal-preventives"), "permission_domain": "client_portal_preventives", "permission_action": "view"},
                ],
                permission_map,
            ),
        }

    @classmethod
    def compose_response(cls, *, request, tenant_context, query: str, resolved: dict, permission_map: dict | None):
        intent = cls.classify_intent(query)
        if intent.key == "report_explanation" and resolved.get("report"):
            response = cls._report_response(payload=resolved["report"], permission_map=permission_map)
        elif intent.key == "quote_explanation" and resolved.get("quote"):
            response = cls._quote_response(payload=resolved["quote"], permission_map=permission_map)
        elif intent.key == "work_order_status" and resolved.get("work_order"):
            response = cls._work_order_response(payload=resolved["work_order"], permission_map=permission_map)
        elif intent.key == "preventive_status" and resolved.get("preventive"):
            response = cls._preventive_response(payload=resolved["preventive"], permission_map=permission_map)
        elif intent.key == "asset_summary" and resolved.get("asset"):
            response = cls._asset_response(asset_payload=resolved["asset"], permission_map=permission_map)
        elif intent.key == "pending_actions":
            response = cls._pending_response(request=request, tenant_context=tenant_context, permission_map=permission_map)
        elif intent.key == "comparison":
            response = cls._comparison_response(request=request, tenant_context=tenant_context, permission_map=permission_map)
        elif resolved.get("contract"):
            response = cls._contract_response(payload=resolved["contract"], permission_map=permission_map)
        elif resolved.get("request"):
            request_payload = resolved["request"]["client_request"]
            response = {
                "response_type": "status_explanation",
                "summary": f"A solicitacao {request_payload.protocol_number} esta {request_payload.get_status_display().lower()}.",
                "bullets": [
                    request_payload.title,
                    request_payload.resolution_summary or "Aguardando nova atualizacao operacional.",
                    "Voce pode acompanhar o protocolo e a OS vinculada, quando existir, pelo portal.",
                ],
                "cards": [
                    {"label": "Solicitacao", "value": request_payload.protocol_number, "meta": request_payload.get_priority_display()},
                ],
                "actions": cls._filter_actions(
                    [
                        {"label": "Abrir solicitacao", "href": reverse("admin-shell:client-portal-request-detail", kwargs={"protocol_number": request_payload.protocol_number}), "permission_domain": "client_portal_requests", "permission_action": "view"},
                        {"label": "Nova solicitacao", "href": reverse("admin-shell:client-portal-request-create"), "permission_domain": "client_portal_requests", "permission_action": "create"},
                    ],
                    permission_map,
                ),
            }
        else:
            response = cls._site_summary_response(
                request=request,
                tenant_context=tenant_context,
                resolved=resolved,
                permission_map=permission_map,
            )
        response["intent"] = intent.key
        return response

    @classmethod
    def _build_session_context(cls, *, tenant_context, resolved: dict, response: dict):
        context = {
            "company_id": tenant_context.get("company").id if tenant_context.get("company") else None,
            "site_code": tenant_context.get("site").code if tenant_context.get("site") else "",
            "intent": response.get("intent", ""),
            "last_summary": response.get("summary", ""),
        }
        if resolved.get("site"):
            context["site_code"] = resolved["site"].code
        if resolved.get("asset"):
            context["asset_code"] = resolved["asset"]["asset"].asset_tag
        if resolved.get("work_order"):
            context["work_order_code"] = resolved["work_order"]["work_order"].order_number
        if resolved.get("quote"):
            context["quote_number"] = resolved["quote"]["quote"].quote_number
        if resolved.get("contract"):
            context["contract_number"] = resolved["contract"]["contract"].contract_number
        if resolved.get("preventive"):
            context["preventive_public_id"] = str(resolved["preventive"]["plan"].public_id)
        if resolved.get("request"):
            context["protocol_number"] = resolved["request"]["client_request"].protocol_number
        if resolved.get("report"):
            context["report_type"] = resolved["report"]["report"]["report_type"]
            context["report_reference"] = resolved["report"]["report"]["reference_code"]
        return context

    @classmethod
    def get_current_context_payload(cls, *, request, tenant_context, permission_map, session_public_id=None, context_seed=None):
        session = cls.get_or_create_session(
            user=request.user,
            tenant_context=tenant_context,
            session_public_id=session_public_id,
        )
        configuration = cls.get_configuration(company=tenant_context.get("company"))
        suggestions = list((configuration.default_suggestions if configuration else []) or cls.DEFAULT_SUGGESTIONS)
        resolved = cls._resolve_entities(
            request=request,
            tenant_context=tenant_context,
            query="",
            context_seed=context_seed,
            session_context=session.current_context,
        )
        context = {
            "company_name": getattr(tenant_context.get("company"), "name", ""),
            "site_name": getattr(tenant_context.get("site"), "name", "Todas as unidades autorizadas"),
            "current_context": session.current_context,
            "available_cards": cls._dashboard_cards(request, tenant_context),
            "resolved_entities": {
                "asset": getattr(resolved.get("asset", {}).get("asset"), "asset_tag", "") if resolved.get("asset") else "",
                "work_order": getattr(resolved.get("work_order", {}).get("work_order"), "order_number", "") if resolved.get("work_order") else "",
                "quote": getattr(resolved.get("quote", {}).get("quote"), "quote_number", "") if resolved.get("quote") else "",
            },
        }
        SystemEventService.log_system_event(
            event_type="copilot.client.context.resolved",
            source_module="client_portal",
            message="Client portal copilot context resolved.",
            user=request.user,
            company=tenant_context.get("company"),
            site=tenant_context.get("site"),
            entity_type="client_portal_copilot_session",
            entity_id=str(session.public_id),
            payload={"session_public_id": str(session.public_id), "request_id": get_request_id()},
        )
        return {"session": session, "context": context, "suggestions": suggestions}

    @classmethod
    @transaction.atomic
    def handle_query(cls, *, request, tenant_context, permission_map, query: str, session_public_id=None, context_seed=None):
        started_at = timezone.now()
        session = cls.get_or_create_session(
            user=request.user,
            tenant_context=tenant_context,
            session_public_id=session_public_id,
        )
        SystemEventService.log_system_event(
            event_type="copilot.client.query.received",
            source_module="client_portal",
            message="Client portal copilot query received.",
            user=request.user,
            company=tenant_context.get("company"),
            site=tenant_context.get("site"),
            entity_type="client_portal_copilot_session",
            entity_id=str(session.public_id),
            payload={"query": query, "request_id": get_request_id()},
        )
        resolved = cls._resolve_entities(
            request=request,
            tenant_context=tenant_context,
            query=query,
            context_seed=context_seed,
            session_context=session.current_context,
        )
        response = cls.compose_response(
            request=request,
            tenant_context=tenant_context,
            query=query,
            resolved=resolved,
            permission_map=permission_map,
        )
        session_context = cls._build_session_context(
            tenant_context=tenant_context,
            resolved=resolved,
            response=response,
        )
        ClientPortalCopilotMessage.objects.create(
            session=session,
            role=ClientPortalCopilotMessage.Role.USER,
            content=query,
            detected_intent=response["intent"],
            context_snapshot=session.current_context,
        )
        ClientPortalCopilotMessage.objects.create(
            session=session,
            role=ClientPortalCopilotMessage.Role.ASSISTANT,
            content=response["summary"],
            detected_intent=response["intent"],
            context_snapshot=session_context,
            structured_payload=response,
        )
        session.current_context = session_context
        session.last_intent = response["intent"]
        session.last_query = query
        session.message_count = session.messages.count()
        session.status = ClientPortalCopilotSession.Status.ACTIVE
        session.save(
            update_fields=[
                "current_context",
                "last_intent",
                "last_query",
                "message_count",
                "status",
                "last_activity_at",
                "updated_at",
            ]
        )
        event_type = "copilot.client.response.generated"
        if response["response_type"] == "report_explanation":
            event_type = "copilot.client.document.explained"
        SystemEventService.log_system_event(
            event_type=event_type,
            source_module="client_portal",
            message="Client portal copilot response generated.",
            user=request.user,
            company=tenant_context.get("company"),
            site=tenant_context.get("site"),
            entity_type="client_portal_copilot_session",
            entity_id=str(session.public_id),
            payload={
                "intent": response["intent"],
                "response_type": response["response_type"],
                "duration_ms": int((timezone.now() - started_at).total_seconds() * 1000),
            },
        )
        if response.get("actions"):
            SystemEventService.log_system_event(
                event_type="copilot.client.action.suggested",
                source_module="client_portal",
                message="Client portal copilot suggested actions.",
                user=request.user,
                company=tenant_context.get("company"),
                site=tenant_context.get("site"),
                entity_type="client_portal_copilot_session",
                entity_id=str(session.public_id),
                payload={"actions": [action["label"] for action in response["actions"][:4]]},
            )
        configuration = cls.get_configuration(company=tenant_context.get("company"))
        suggestions = list((configuration.default_suggestions if configuration else []) or cls.DEFAULT_SUGGESTIONS)
        return {
            "session": session,
            "context": session_context,
            "response": response,
            "suggestions": suggestions,
        }

    @classmethod
    def list_pending_cards(cls, *, request, tenant_context, permission_map):
        response = cls._pending_response(request=request, tenant_context=tenant_context, permission_map=permission_map)
        return {
            "summary": response["summary"],
            "bullets": response["bullets"],
            "cards": response["cards"],
            "actions": response["actions"],
        }
