from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import timezone

from apps.ai_agents_center.models import (
    AgentActionProposal,
    AgentAnomalyAttentionFlag,
    AgentAssetAttentionFlag,
    AgentMarketplaceRequestFlag,
    AgentProfitabilityAttentionFlag,
    AgentRecommendation,
    AgentScheduleHealthFlag,
    ManagerCopilotConfiguration,
    ManagerCopilotMessage,
    ManagerCopilotSession,
)
from apps.ai_simulation_engine.models import SimulationRun
from apps.ai_optimization_loop.models import OptimizationProposal
from apps.ai_optimization_loop.services.quality import OptimizationQualityService
from apps.analytics_platform.models import OperationalMetrics
from apps.analytics_platform.services.analytics_service import ExecutiveAnalyticsService
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import Asset, FailureEvent, MaintenanceClient, MaintenanceContract, OperationalSite, ServiceOrder
from shared_kernel.observability.context import get_request_id


User = get_user_model()


def _json_ready(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime, UUID)):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    return value


@dataclass(frozen=True)
class CopilotPeriod:
    key: str
    start: timezone.datetime.date
    end: timezone.datetime.date
    label: str
    comparison_start: timezone.datetime.date
    comparison_end: timezone.datetime.date
    comparison_label: str
    target_date: timezone.datetime.date | None = None


class ManagerCopilotService:
    DEFAULT_SUGGESTIONS = [
        "Quais sao os maiores riscos operacionais hoje?",
        "Resuma a situacao desta unidade nesta semana.",
        "Quais recomendacoes pendentes eu deveria olhar primeiro?",
        "Tem algum contrato dando prejuizo?",
        "Quais tecnicos estao sobrecarregados amanha?",
        "Mostre os principais desvios anomalos recentes.",
    ]

    INTENT_KEYWORDS = {
        "comparison": ["comparado", "comparar", "mudou", "mudanca", "semana passada", "mes passado", "ontem"],
        "simulation": ["impacto", "simular", "simulacao", "trade-off", "tradeoff", "vale a pena", "cenario", "compare esse cenario"],
        "quality": ["qualidade", "efetividade", "assertividade", "aprendizado", "otimizacao", "optimization"],
        "risk_anomaly": ["risco", "anomalia", "desvio", "problema", "gargalo", "alerta"],
        "profitability": ["margem", "lucro", "prejuizo", "rentabilidade", "contrato", "cliente deficitario", "custo"],
        "scheduling": ["agenda", "tecnico", "tecnicos", "sobrecarregado", "amanha", "sla", "rota", "visita"],
        "maintenance": ["ativo", "falha", "preventiva", "preventivo", "rca", "confiabilidade"],
        "marketplace": ["marketplace", "request", "assignment", "alocacao", "oferta", "candidato"],
        "recommendation_action": ["recomendacao", "recomendacoes", "pendente", "aprovar", "rejeitar", "acao"],
        "investigation": ["explique", "por que", "porque", "detalhe", "entender", "investigar"],
    }

    @classmethod
    def get_or_create_session(cls, *, user, tenant_context, session_public_id=None):
        company = tenant_context.get("company")
        site = tenant_context.get("site")
        queryset = ManagerCopilotSession.objects.select_related("company", "site").filter(user=user)
        if company is not None:
            queryset = queryset.filter(company=company)
        if site is not None:
            queryset = queryset.filter(site=site)
        if session_public_id:
            session = queryset.filter(public_id=session_public_id).first()
            if session is not None:
                return session
        latest_session = queryset.order_by("-last_activity_at").first()
        if latest_session is not None:
            return latest_session
        return ManagerCopilotSession.objects.create(
            user=user,
            company=company,
            site=site,
            status=ManagerCopilotSession.Status.ACTIVE,
            title="Copilot do gestor",
            current_context={},
        )

    @classmethod
    def get_configuration(cls, *, company=None):
        configuration = None
        if company is not None:
            configuration = ManagerCopilotConfiguration.objects.filter(company=company).first()
        if configuration is None:
            configuration = ManagerCopilotConfiguration.objects.filter(company__isnull=True).first()
        return configuration

    @classmethod
    def classify_intent(cls, query: str) -> str:
        normalized = (query or "").strip().lower()
        if not normalized:
            return "executive_summary"
        for intent, keywords in cls.INTENT_KEYWORDS.items():
            if any(keyword in normalized for keyword in keywords):
                return intent
        if any(token in normalized for token in ["resuma", "como esta", "situacao", "status"]):
            return "executive_summary"
        return "investigation"

    @classmethod
    def resolve_period(cls, *, query: str, session_context: dict | None = None) -> CopilotPeriod:
        today = timezone.localdate()
        normalized = (query or "").lower()
        session_context = session_context or {}
        if "amanha" in normalized:
            target_date = today + timedelta(days=1)
            return CopilotPeriod(
                key="tomorrow",
                start=target_date,
                end=target_date,
                label=f"Amanha ({target_date:%d/%m/%Y})",
                comparison_start=today,
                comparison_end=today,
                comparison_label=f"Hoje ({today:%d/%m/%Y})",
                target_date=target_date,
            )
        if "semana passada" in normalized:
            end = today - timedelta(days=today.weekday() + 1)
            start = end - timedelta(days=6)
            comparison_end = start - timedelta(days=1)
            comparison_start = comparison_end - timedelta(days=6)
            return CopilotPeriod(
                key="last_week",
                start=start,
                end=end,
                label="Semana passada",
                comparison_start=comparison_start,
                comparison_end=comparison_end,
                comparison_label="Semana anterior",
            )
        if "esta semana" in normalized or "nessa semana" in normalized or "nesta semana" in normalized:
            start = today - timedelta(days=today.weekday())
            end = today
            comparison_end = start - timedelta(days=1)
            comparison_start = comparison_end - timedelta(days=(end - start).days)
            return CopilotPeriod(
                key="this_week",
                start=start,
                end=end,
                label="Esta semana",
                comparison_start=comparison_start,
                comparison_end=comparison_end,
                comparison_label="Periodo anterior equivalente",
            )
        if "mes passado" in normalized:
            start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            end = today.replace(day=1) - timedelta(days=1)
            comparison_end = start - timedelta(days=1)
            comparison_start = comparison_end.replace(day=1)
            return CopilotPeriod(
                key="last_month",
                start=start,
                end=end,
                label="Mes passado",
                comparison_start=comparison_start,
                comparison_end=comparison_end,
                comparison_label="Mes anterior",
            )
        if "hoje" in normalized:
            return CopilotPeriod(
                key="today",
                start=today,
                end=today,
                label=f"Hoje ({today:%d/%m/%Y})",
                comparison_start=today - timedelta(days=1),
                comparison_end=today - timedelta(days=1),
                comparison_label="Ontem",
                target_date=today,
            )
        if session_context.get("period"):
            period = session_context["period"]
            return CopilotPeriod(
                key=period.get("key", "rolling_30d"),
                start=timezone.datetime.strptime(period["start"], "%Y-%m-%d").date(),
                end=timezone.datetime.strptime(period["end"], "%Y-%m-%d").date(),
                label=period.get("label", "Periodo atual"),
                comparison_start=timezone.datetime.strptime(period["comparison_start"], "%Y-%m-%d").date(),
                comparison_end=timezone.datetime.strptime(period["comparison_end"], "%Y-%m-%d").date(),
                comparison_label=period.get("comparison_label", "Periodo anterior"),
                target_date=timezone.datetime.strptime(period["target_date"], "%Y-%m-%d").date()
                if period.get("target_date")
                else None,
            )
        start = today - timedelta(days=29)
        end = today
        comparison_end = start - timedelta(days=1)
        comparison_start = comparison_end - timedelta(days=29)
        return CopilotPeriod(
            key="rolling_30d",
            start=start,
            end=end,
            label="Ultimos 30 dias",
            comparison_start=comparison_start,
            comparison_end=comparison_end,
            comparison_label="30 dias anteriores",
        )

    @classmethod
    def _contains_any(cls, query: str, candidates: list[str]) -> bool:
        lowered = query.lower()
        return any(candidate and candidate.lower() in lowered for candidate in candidates)

    @classmethod
    def _resolve_entities(cls, *, query: str, company, site, context_seed: dict | None = None):
        context_seed = context_seed or {}
        resolved = {}
        asset_public_id = context_seed.get("asset_public_id") or context_seed.get("asset")
        site_public_id = context_seed.get("site_public_id") or context_seed.get("site")
        client_public_id = context_seed.get("client_public_id") or context_seed.get("client")
        contract_public_id = context_seed.get("contract_public_id") or context_seed.get("contract")
        technician_id = context_seed.get("technician_id") or context_seed.get("technician")

        asset_queryset = Asset.objects.select_related("operational_site", "category")
        site_queryset = OperationalSite.objects.select_related("maintenance_client")
        client_queryset = MaintenanceClient.objects.all()
        contract_queryset = MaintenanceContract.objects.select_related("client", "operational_site")
        technician_queryset = User.objects.all()

        if company is not None:
            asset_queryset = asset_queryset.filter(operational_site__maintenance_client__company=company)
            site_queryset = site_queryset.filter(maintenance_client__company=company)
            client_queryset = client_queryset.filter(company=company)
            contract_queryset = contract_queryset.filter(company=company)
            technician_queryset = technician_queryset.filter(memberships__company=company).distinct()
        if site is not None:
            asset_queryset = asset_queryset.filter(operational_site=site)
            contract_queryset = contract_queryset.filter(operational_site=site)

        if asset_public_id:
            resolved["asset"] = asset_queryset.filter(public_id=asset_public_id).first()
        if site_public_id:
            resolved["site"] = site_queryset.filter(public_id=site_public_id).first()
        if client_public_id:
            resolved["client"] = client_queryset.filter(public_id=client_public_id).first()
        if contract_public_id:
            resolved["contract"] = contract_queryset.filter(public_id=contract_public_id).first()
        if technician_id:
            resolved["technician"] = technician_queryset.filter(pk=technician_id).first()

        normalized = (query or "").lower()
        if not resolved.get("site"):
            for candidate in site_queryset[:25]:
                if cls._contains_any(normalized, [candidate.name, candidate.code]):
                    resolved["site"] = candidate
                    break
        if not resolved.get("asset"):
            for candidate in asset_queryset[:40]:
                if cls._contains_any(normalized, [candidate.asset_tag, candidate.name]):
                    resolved["asset"] = candidate
                    break
        if not resolved.get("client"):
            for candidate in client_queryset[:25]:
                if cls._contains_any(normalized, [candidate.display_name, candidate.legal_name]):
                    resolved["client"] = candidate
                    break
        if not resolved.get("contract"):
            for candidate in contract_queryset[:25]:
                if cls._contains_any(normalized, [candidate.contract_number, candidate.client.display_name]):
                    resolved["contract"] = candidate
                    break
        if not resolved.get("technician"):
            for candidate in technician_queryset[:25]:
                display_name = getattr(candidate, "display_name", "") or candidate.get_full_name() or candidate.email
                if cls._contains_any(normalized, [display_name, candidate.first_name, candidate.last_name, candidate.email]):
                    resolved["technician"] = candidate
                    break
        return resolved

    @classmethod
    def resolve_current_context(cls, *, user, tenant_context, query="", session=None, context_seed=None):
        company = tenant_context.get("company")
        site = tenant_context.get("site")
        session_context = (session.current_context if session else {}) or {}
        period = cls.resolve_period(query=query, session_context=session_context)
        resolved_entities = cls._resolve_entities(query=query, company=company, site=site, context_seed=context_seed)

        if resolved_entities.get("site") is not None:
            site = resolved_entities["site"]

        context = {
            "company_id": company.id if company else session_context.get("company_id"),
            "company_name": getattr(company, "name", session_context.get("company_name", "")),
            "site_id": site.id if site else session_context.get("site_id"),
            "site_public_id": str(site.public_id) if site else session_context.get("site_public_id", ""),
            "site_name": getattr(site, "name", session_context.get("site_name", "")),
            "intent": cls.classify_intent(query),
            "period": {
                "key": period.key,
                "start": period.start.isoformat(),
                "end": period.end.isoformat(),
                "label": period.label,
                "comparison_start": period.comparison_start.isoformat(),
                "comparison_end": period.comparison_end.isoformat(),
                "comparison_label": period.comparison_label,
                "target_date": period.target_date.isoformat() if period.target_date else "",
            },
        }

        for entity_name, entity in resolved_entities.items():
            if entity is None:
                continue
            if entity_name == "asset":
                context["asset_public_id"] = str(entity.public_id)
                context["asset_label"] = f"{entity.asset_tag} - {entity.name}"
                if not context.get("site_public_id"):
                    context["site_public_id"] = str(entity.operational_site.public_id)
                    context["site_id"] = entity.operational_site_id
                    context["site_name"] = entity.operational_site.name
            elif entity_name == "site":
                context["site_public_id"] = str(entity.public_id)
                context["site_id"] = entity.id
                context["site_name"] = entity.name
            elif entity_name == "client":
                context["client_public_id"] = str(entity.public_id)
                context["client_label"] = entity.display_name
            elif entity_name == "contract":
                context["contract_public_id"] = str(entity.public_id)
                context["contract_label"] = entity.contract_number
            elif entity_name == "technician":
                context["technician_id"] = entity.id
                context["technician_label"] = getattr(entity, "display_name", "") or entity.get_full_name() or entity.email
        return context

    @classmethod
    def _scoped_recommendations(cls, *, company, context):
        queryset = AgentRecommendation.objects.select_related("agent_run", "agent_run__agent", "site", "company").all()
        if company is not None:
            queryset = queryset.filter(company=company)
        site_public_id = context.get("site_public_id")
        asset_public_id = context.get("asset_public_id")
        client_public_id = context.get("client_public_id")
        contract_public_id = context.get("contract_public_id")
        technician_id = context.get("technician_id")
        if site_public_id:
            queryset = queryset.filter(site__public_id=site_public_id)
        if asset_public_id:
            queryset = queryset.filter(Q(entity_type="asset", entity_id=asset_public_id) | Q(payload__asset__public_id=asset_public_id))
        if client_public_id:
            queryset = queryset.filter(
                Q(entity_type="maintenance_client", entity_id=client_public_id)
                | Q(payload__client_public_id=client_public_id)
            )
        if contract_public_id:
            queryset = queryset.filter(
                Q(entity_type="maintenance_contract", entity_id=contract_public_id)
                | Q(payload__contract_public_id=contract_public_id)
            )
        if technician_id:
            queryset = queryset.filter(
                Q(entity_type="user", entity_id=str(technician_id))
                | Q(payload__technician__technician_id=technician_id)
            )
        return queryset

    @classmethod
    def _scoped_proposals(cls, *, company, context):
        queryset = AgentActionProposal.objects.select_related("agent_run", "agent_run__agent", "agent_run__company").all()
        if company is not None:
            queryset = queryset.filter(agent_run__company=company)
        asset_public_id = context.get("asset_public_id")
        client_public_id = context.get("client_public_id")
        contract_public_id = context.get("contract_public_id")
        technician_id = context.get("technician_id")
        if asset_public_id:
            queryset = queryset.filter(target_entity="asset", target_entity_id=asset_public_id)
        if client_public_id:
            queryset = queryset.filter(
                Q(target_entity="maintenance_client", target_entity_id=client_public_id)
                | Q(proposed_payload__client_public_id=client_public_id)
            )
        if contract_public_id:
            queryset = queryset.filter(
                Q(target_entity="maintenance_contract", target_entity_id=contract_public_id)
                | Q(proposed_payload__contract_public_id=contract_public_id)
            )
        if technician_id:
            queryset = queryset.filter(
                Q(proposed_payload__technician_id=technician_id)
                | Q(proposed_payload__from_technician_id=technician_id)
                | Q(proposed_payload__to_technician_id=technician_id)
            )
        return queryset

    @classmethod
    def aggregate_recommendations(cls, *, company, context):
        queryset = cls._scoped_recommendations(company=company, context=context).exclude(status=AgentRecommendation.Status.DISMISSED)
        ordered = queryset.order_by(
            "-attention_score",
            "-created_at",
        )
        seen = set()
        cards = []
        for recommendation in ordered[:40]:
            dedupe_key = (recommendation.recommendation_type, recommendation.entity_type, recommendation.entity_id)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            cards.append(
                {
                    "public_id": str(recommendation.public_id),
                    "title": recommendation.title,
                    "summary": recommendation.summary,
                    "explanation": recommendation.explanation or recommendation.summary,
                    "evidence_summary": recommendation.evidence_summary,
                    "suggested_action": recommendation.suggested_action,
                    "severity": recommendation.severity,
                    "priority": recommendation.priority,
                    "status": recommendation.status,
                    "attention_score": recommendation.attention_score,
                    "agent_slug": recommendation.agent_run.agent.slug,
                    "agent_name": recommendation.agent_run.agent.name,
                    "requires_human_approval": recommendation.requires_human_approval,
                    "entity_type": recommendation.entity_type,
                    "entity_id": recommendation.entity_id,
                    "detail_href": cls._build_recommendation_href(recommendation),
                }
            )
            if len(cards) >= 12:
                break
        return cards

    @classmethod
    def aggregate_proposals(cls, *, company, context):
        queryset = cls._scoped_proposals(company=company, context=context).order_by("-created_at")
        cards = []
        for proposal in queryset[:10]:
            cards.append(
                {
                    "public_id": str(proposal.public_id),
                    "title": proposal.title or proposal.action_type,
                    "summary": proposal.summary or proposal.action_type,
                    "action_type": proposal.action_type,
                    "priority": proposal.priority,
                    "status": proposal.status,
                    "approval_required": proposal.approval_required,
                    "agent_name": proposal.agent_run.agent.name,
                    "approve_href": reverse("admin-shell:ai-agents-proposal-approve", kwargs={"proposal_id": proposal.public_id}),
                    "reject_href": reverse("admin-shell:ai-agents-proposal-reject", kwargs={"proposal_id": proposal.public_id}),
                }
            )
        return cards

    @classmethod
    def _build_recommendation_href(cls, recommendation):
        route_map = {
            "maintenance-agent": "admin-shell:ai-agents-maintenance-health",
            "scheduling-agent": "admin-shell:ai-agents-scheduling-health",
            "profitability-agent": "admin-shell:ai-agents-profitability-health",
            "marketplace-agent": "admin-shell:ai-agents-marketplace-health",
            "anomaly-agent": "admin-shell:ai-agents-anomaly-health",
        }
        route_name = route_map.get(recommendation.agent_run.agent.slug, "admin-shell:ai-agents-recommendations")
        return reverse(route_name)

    @classmethod
    def _build_flag_cards(cls, *, company, context):
        site_public_id = context.get("site_public_id")
        asset_public_id = context.get("asset_public_id")
        client_public_id = context.get("client_public_id")
        contract_public_id = context.get("contract_public_id")
        technician_id = context.get("technician_id")
        target_date = context.get("period", {}).get("target_date")

        cards = []
        asset_flags = AgentAssetAttentionFlag.objects.select_related("asset", "latest_recommendation").filter(company=company) if company else AgentAssetAttentionFlag.objects.none()
        if site_public_id:
            asset_flags = asset_flags.filter(site__public_id=site_public_id)
        if asset_public_id:
            asset_flags = asset_flags.filter(asset__public_id=asset_public_id)
        for flag in asset_flags.order_by("-attention_score")[:3]:
            cards.append(
                {
                    "theme": "maintenance",
                    "title": flag.asset.asset_tag,
                    "summary": flag.summary,
                    "severity": flag.risk_level,
                    "attention_score": flag.attention_score,
                    "href": reverse("admin-shell:ai-agents-maintenance-health"),
                }
            )

        schedule_flags = AgentScheduleHealthFlag.objects.select_related("technician").filter(company=company) if company else AgentScheduleHealthFlag.objects.none()
        if site_public_id:
            schedule_flags = schedule_flags.filter(site__public_id=site_public_id)
        if technician_id:
            schedule_flags = schedule_flags.filter(technician_id=technician_id)
        if target_date:
            schedule_flags = schedule_flags.filter(schedule_date=target_date)
        for flag in schedule_flags.order_by("-attention_score")[:3]:
            technician_name = getattr(flag.technician, "display_name", "") or getattr(flag.technician, "email", "") or "Tecnico"
            cards.append(
                {
                    "theme": "scheduling",
                    "title": technician_name,
                    "summary": flag.summary,
                    "severity": flag.risk_level,
                    "attention_score": flag.attention_score,
                    "href": reverse("admin-shell:ai-agents-scheduling-health"),
                }
            )

        profitability_flags = AgentProfitabilityAttentionFlag.objects.filter(company=company) if company else AgentProfitabilityAttentionFlag.objects.none()
        if site_public_id:
            profitability_flags = profitability_flags.filter(site__public_id=site_public_id)
        if client_public_id:
            profitability_flags = profitability_flags.filter(client__public_id=client_public_id)
        if contract_public_id:
            profitability_flags = profitability_flags.filter(contract__public_id=contract_public_id)
        if technician_id:
            profitability_flags = profitability_flags.filter(technician_id=technician_id)
        for flag in profitability_flags.order_by("-attention_score")[:3]:
            cards.append(
                {
                    "theme": "profitability",
                    "title": flag.display_label,
                    "summary": flag.summary,
                    "severity": flag.risk_level,
                    "attention_score": flag.attention_score,
                    "href": reverse("admin-shell:ai-agents-profitability-health"),
                }
            )

        marketplace_flags = AgentMarketplaceRequestFlag.objects.select_related("service_request").filter(company=company) if company else AgentMarketplaceRequestFlag.objects.none()
        if site_public_id:
            marketplace_flags = marketplace_flags.filter(site__public_id=site_public_id)
        for flag in marketplace_flags.order_by("-attention_score")[:2]:
            cards.append(
                {
                    "theme": "marketplace",
                    "title": flag.service_request.title,
                    "summary": flag.summary,
                    "severity": flag.risk_level,
                    "attention_score": flag.attention_score,
                    "href": reverse("admin-shell:ai-agents-marketplace-health"),
                }
            )

        anomaly_flags = AgentAnomalyAttentionFlag.objects.filter(company=company) if company else AgentAnomalyAttentionFlag.objects.none()
        if site_public_id:
            anomaly_flags = anomaly_flags.filter(site__public_id=site_public_id)
        if asset_public_id:
            anomaly_flags = anomaly_flags.filter(asset__public_id=asset_public_id)
        if client_public_id:
            anomaly_flags = anomaly_flags.filter(client__public_id=client_public_id)
        if contract_public_id:
            anomaly_flags = anomaly_flags.filter(contract__public_id=contract_public_id)
        if technician_id:
            anomaly_flags = anomaly_flags.filter(technician_id=technician_id)
        for flag in anomaly_flags.order_by("-attention_score")[:3]:
            cards.append(
                {
                    "theme": "anomaly",
                    "title": flag.display_label,
                    "summary": flag.summary,
                    "severity": flag.risk_level,
                    "attention_score": flag.attention_score,
                    "href": reverse("admin-shell:ai-agents-anomaly-health"),
                }
            )
        return sorted(cards, key=lambda item: item["attention_score"], reverse=True)[:8]

    @classmethod
    def _build_company_metrics(cls, *, company, context):
        if company is None:
            return []
        dashboard = ExecutiveAnalyticsService.build_executive_dashboard(
            company=company,
            reference_date=timezone.localdate(),
            period_type=OperationalMetrics.PeriodType.MONTHLY,
        )
        summary_map = {card["label"]: card for card in dashboard["kpis"]}
        metrics = []
        for label in ("Receita operacional", "Lucro operacional", "Contratos ativos", "MRR total", "SLA medio", "Tempo medio de resposta"):
            if label not in summary_map:
                continue
            card = summary_map[label]
            metrics.append(
                {
                    "label": card["label"],
                    "value": card["value"],
                    "format": card.get("format", "text"),
                    "tone": card.get("tone", "neutral"),
                    "helper": card.get("helper", ""),
                }
            )
        metrics.append(
            {
                "label": "Recomendacoes abertas",
                "value": cls._scoped_recommendations(company=company, context=context).filter(status=AgentRecommendation.Status.OPEN).count(),
                "format": "number",
                "tone": "warning",
                "helper": "Itens ainda aguardando tratamento",
            }
        )
        metrics.append(
            {
                "label": "Propostas pendentes",
                "value": cls._scoped_proposals(company=company, context=context).filter(status=AgentActionProposal.Status.PENDING_APPROVAL).count(),
                "format": "number",
                "tone": "warning",
                "helper": "Acoes com human-in-the-loop",
            }
        )
        return metrics[:8]

    @classmethod
    def _build_period_comparison(cls, *, company, context):
        if company is None:
            return {}
        period = context["period"]
        current_start = timezone.datetime.strptime(period["start"], "%Y-%m-%d").date()
        current_end = timezone.datetime.strptime(period["end"], "%Y-%m-%d").date()
        previous_start = timezone.datetime.strptime(period["comparison_start"], "%Y-%m-%d").date()
        previous_end = timezone.datetime.strptime(period["comparison_end"], "%Y-%m-%d").date()

        current_orders = ServiceOrder.objects.filter(
            client__company=company,
            opened_at__date__gte=current_start,
            opened_at__date__lte=current_end,
        )
        previous_orders = ServiceOrder.objects.filter(
            client__company=company,
            opened_at__date__gte=previous_start,
            opened_at__date__lte=previous_end,
        )
        current_failures = FailureEvent.objects.filter(
            asset__operational_site__maintenance_client__company=company,
            created_at__date__gte=current_start,
            created_at__date__lte=current_end,
        )
        previous_failures = FailureEvent.objects.filter(
            asset__operational_site__maintenance_client__company=company,
            created_at__date__gte=previous_start,
            created_at__date__lte=previous_end,
        )
        return {
            "current_label": period["label"],
            "comparison_label": period["comparison_label"],
            "items": [
                {
                    "label": "Ordens de servico",
                    "current": current_orders.count(),
                    "previous": previous_orders.count(),
                    "delta": current_orders.count() - previous_orders.count(),
                },
                {
                    "label": "Corretivas",
                    "current": current_orders.filter(maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE).count(),
                    "previous": previous_orders.filter(maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE).count(),
                    "delta": current_orders.filter(maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE).count()
                    - previous_orders.filter(maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE).count(),
                },
                {
                    "label": "Falhas registradas",
                    "current": current_failures.count(),
                    "previous": previous_failures.count(),
                    "delta": current_failures.count() - previous_failures.count(),
                },
            ],
        }

    @classmethod
    def _build_entity_summary(cls, *, company, context):
        asset_public_id = context.get("asset_public_id")
        client_public_id = context.get("client_public_id")
        contract_public_id = context.get("contract_public_id")
        technician_id = context.get("technician_id")
        site_public_id = context.get("site_public_id")
        now = timezone.localdate()

        if asset_public_id:
            asset = Asset.objects.select_related("operational_site", "category").filter(public_id=asset_public_id).first()
            if asset is not None:
                open_orders = ServiceOrder.objects.filter(asset=asset).exclude(status=ServiceOrder.Status.COMPLETED).count()
                recent_failures = FailureEvent.objects.filter(asset=asset, created_at__date__gte=now - timedelta(days=30)).count()
                return {
                    "scope_label": f"Ativo {asset.asset_tag}",
                    "summary": f"{asset.name} em {asset.operational_site.name} com {recent_failures} falhas recentes e {open_orders} OS abertas.",
                }
        if contract_public_id:
            contract = MaintenanceContract.objects.select_related("client", "operational_site").filter(public_id=contract_public_id).first()
            if contract is not None:
                order_count = ServiceOrder.objects.filter(maintenance_contract=contract).count()
                return {
                    "scope_label": f"Contrato {contract.contract_number}",
                    "summary": f"Contrato de {contract.client.display_name} com {order_count} OS vinculadas e acompanhamento economico ativo.",
                }
        if client_public_id:
            client = MaintenanceClient.objects.filter(public_id=client_public_id).first()
            if client is not None:
                contract_count = MaintenanceContract.objects.filter(client=client).count()
                return {
                    "scope_label": f"Cliente {client.display_name}",
                    "summary": f"Cliente com {contract_count} contratos recorrentes e monitoramento de margem, backlog e corretivas.",
                }
        if technician_id:
            technician = User.objects.filter(pk=technician_id).first()
            if technician is not None:
                visit_count = AgentScheduleHealthFlag.objects.filter(company=company, technician=technician).count() if company else 0
                label = getattr(technician, "display_name", "") or technician.get_full_name() or technician.email
                return {
                    "scope_label": f"Tecnico {label}",
                    "summary": f"Visao da capacidade, agenda e alertas operacionais do tecnico com {visit_count} sinais persistidos.",
                }
        if site_public_id:
            site = OperationalSite.objects.select_related("maintenance_client").filter(public_id=site_public_id).first()
            if site is not None:
                asset_count = Asset.objects.filter(operational_site=site).count()
                return {
                    "scope_label": f"Unidade {site.name}",
                    "summary": f"Unidade de {site.maintenance_client.display_name} com {asset_count} ativos sob observacao operacional e executiva.",
                }
        if company is not None:
            return {
                "scope_label": company.name,
                "summary": f"Leitura consolidada da operacao de {company.name} no escopo atual do gestor.",
            }
        return {
            "scope_label": "Sem empresa ativa",
            "summary": "Selecione uma empresa para o copiloto responder com contexto real e seguro.",
        }

    @classmethod
    def build_action_links(cls, *, context, recommendations, proposals):
        links = [
            {"label": "Abrir AI Agents Center", "href": reverse("admin-shell:ai-agents-dashboard")},
            {"label": "Ver recomendacoes", "href": reverse("admin-shell:ai-agents-recommendations")},
        ]
        if context.get("asset_public_id"):
            asset = Asset.objects.filter(public_id=context["asset_public_id"]).first()
            if asset is not None:
                links.append(
                    {
                        "label": "Abrir ativo em foco",
                        "href": reverse("admin-shell:smart-system-asset-detail", kwargs={"asset_code": asset.asset_tag}),
                    }
                )
        if context.get("contract_public_id"):
            contract = MaintenanceContract.objects.filter(public_id=context["contract_public_id"]).first()
            if contract is not None:
                links.append(
                    {
                        "label": "Abrir contrato",
                        "href": reverse(
                            "admin-shell:smart-system-contract-detail",
                            kwargs={"contract_number": contract.contract_number},
                        ),
                    }
                )
        if context.get("technician_id"):
            links.append({"label": "Ver agenda do tecnico", "href": reverse("admin-shell:smart-system-scheduling")})
        if any(card["agent_slug"] == "anomaly-agent" for card in recommendations):
            links.append({"label": "Ver anomalias recentes", "href": reverse("admin-shell:ai-agents-anomaly-health")})
        if proposals:
            links.append({"label": "Aprovar propostas pendentes", "href": reverse("admin-shell:ai-agents-proposals")})
        if context.get("intent") == "quality":
            links.append({"label": "Abrir optimization loop", "href": reverse("admin-shell:ai-optimization-center")})
        deduped = []
        seen = set()
        for link in links:
            key = (link["label"], link["href"])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(link)
        return deduped[:6]

    @classmethod
    def compose_response(cls, *, query, context, company, recommendations, proposals, flag_cards, metrics, comparison, entity_summary):
        priorities = []
        for card in flag_cards[:4]:
            priorities.append(f"{card['title']}: {card['summary']}")
        if not priorities and recommendations:
            priorities = [item["summary"] for item in recommendations[:4]]
        if not priorities:
            priorities = ["Nenhum alerta critico aberto no escopo atual.", "Continuar monitorando backlog, SLA e margem."]

        summary = entity_summary["summary"]
        if recommendations:
            summary += f" Ha {len(recommendations)} recomendacoes relevantes e {len(proposals)} propostas em fila."
        simulations = cls._recent_simulation_cards(company=company, context=context)
        quality_cards = cls._quality_cards(company=company)
        if context["intent"] == "simulation" and simulations:
            top_simulation = simulations[0]
            summary += (
                f" A simulacao mais relevante indica: {top_simulation['summary']} "
                f"Confianca {top_simulation['confidence_level']}."
            )
        elif context["intent"] == "quality" and quality_cards:
            top_quality = quality_cards[0]
            summary += f" O principal sinal de qualidade agora e {top_quality['title']}: {top_quality['summary']}."
        response_type = "executive_summary"
        if context["intent"] == "comparison":
            response_type = "comparison"
        elif context["intent"] == "simulation":
            response_type = "simulation"
        elif context["intent"] == "quality":
            response_type = "optimization"
        elif context["intent"] in {"recommendation_action", "investigation"}:
            response_type = "action_guided"
        elif context["intent"] in {"risk_anomaly", "maintenance", "scheduling", "profitability", "marketplace"}:
            response_type = "analytical"
        return {
            "response_type": response_type,
            "headline": entity_summary["scope_label"],
            "summary": summary,
            "priorities": priorities[:5],
            "risk_cards": flag_cards[:6],
            "recommendation_cards": recommendations[:6],
            "proposal_cards": proposals[:5],
            "metrics": metrics,
            "comparison": comparison,
            "simulation_cards": simulations[:4],
            "quality_cards": quality_cards[:4],
            "action_links": cls.build_action_links(context=context, recommendations=recommendations, proposals=proposals),
            "question": query,
        }

    @classmethod
    def _recent_simulation_cards(cls, *, company, context):
        if company is None:
            return []
        queryset = SimulationRun.objects.select_related("scenario", "scenario__simulation_type", "result").filter(
            scenario__company=company,
            status=SimulationRun.RunStatus.COMPLETED,
        )
        if context.get("site_id"):
            queryset = queryset.filter(Q(scenario__site_id=context["site_id"]) | Q(scenario__site__isnull=True))
        if context.get("asset_public_id"):
            queryset = queryset.filter(
                Q(scenario__target_entity="asset", scenario__target_entity_id=context["asset_public_id"])
                | Q(input_payload__asset_public_id=context["asset_public_id"])
            )
        queryset = queryset.order_by("-created_at")[:6]
        return [
            {
                "simulation_type": item.scenario.simulation_type.slug,
                "summary": item.result.summary if hasattr(item, "result") else "",
                "confidence_level": item.result.confidence_level if hasattr(item, "result") else "low",
                "impact_score": str(item.result.impact_score) if hasattr(item, "result") else "0",
            }
            for item in queryset
        ]

    @classmethod
    def _quality_cards(cls, *, company):
        if company is None:
            return []
        overview = OptimizationQualityService.overview(company=company)
        proposals = OptimizationProposal.objects.filter(company=company).order_by("-created_at")[:3]
        cards = [
            {
                "title": "Decisoes executadas",
                "summary": f"Score medio {overview['decision_avg']:.2f} nas decisoes observadas.",
            },
            {
                "title": "Simulacoes observadas",
                "summary": f"Score medio {overview['simulation_avg']:.2f} na aderencia entre previsto e realizado.",
            },
        ]
        for proposal in proposals:
            cards.append(
                {
                    "title": proposal.proposal_type,
                    "summary": proposal.expected_impact_summary or proposal.rationale,
                }
            )
        return cards[:4]

    @classmethod
    def _session_title(cls, session, query):
        if session.title and session.title != "Copilot do gestor":
            return session.title
        text = (query or "Copilot do gestor").strip()
        return text[:180]

    @classmethod
    @transaction.atomic
    def handle_query(cls, *, user, tenant_context, query, session_public_id=None, context_seed=None):
        session = cls.get_or_create_session(user=user, tenant_context=tenant_context, session_public_id=session_public_id)
        company = tenant_context.get("company")
        site = tenant_context.get("site")
        request_id = get_request_id()
        SystemEventService.log_system_event(
            event_type="copilot.manager.query.received",
            source_module="ai_agents_center",
            message="Manager copilot query received.",
            entity_type="manager_copilot_session",
            entity_id=str(session.public_id),
            user=user,
            company=company,
            site=site,
            payload={"request_id": request_id, "query": query},
        )

        context = cls.resolve_current_context(
            user=user,
            tenant_context=tenant_context,
            query=query,
            session=session,
            context_seed=context_seed,
        )
        SystemEventService.log_system_event(
            event_type="copilot.manager.context.resolved",
            source_module="ai_agents_center",
            message="Manager copilot context resolved.",
            entity_type="manager_copilot_session",
            entity_id=str(session.public_id),
            user=user,
            company=company,
            site=site,
            payload={"request_id": request_id, "intent": context["intent"], "context": context},
        )

        recommendations = cls.aggregate_recommendations(company=company, context=context)
        proposals = cls.aggregate_proposals(company=company, context=context)
        flag_cards = cls._build_flag_cards(company=company, context=context)
        metrics = cls._build_company_metrics(company=company, context=context)
        comparison = cls._build_period_comparison(company=company, context=context)
        entity_summary = cls._build_entity_summary(company=company, context=context)
        response_payload = cls.compose_response(
            query=query,
            context=context,
            company=company,
            recommendations=recommendations,
            proposals=proposals,
            flag_cards=flag_cards,
            metrics=metrics,
            comparison=comparison,
            entity_summary=entity_summary,
        )
        context_snapshot = _json_ready(context)
        response_payload = _json_ready(response_payload)
        referenced_agents = sorted({item["agent_slug"] for item in recommendations})

        ManagerCopilotMessage.objects.create(
            session=session,
            role=ManagerCopilotMessage.Role.USER,
            content=query,
            detected_intent=context_snapshot["intent"],
            context_snapshot=context_snapshot,
            referenced_agents=referenced_agents,
        )
        ManagerCopilotMessage.objects.create(
            session=session,
            role=ManagerCopilotMessage.Role.ASSISTANT,
            content=response_payload["summary"],
            detected_intent=context_snapshot["intent"],
            context_snapshot=context_snapshot,
            referenced_agents=referenced_agents,
            structured_payload=response_payload,
        )
        session.title = cls._session_title(session, query)
        session.status = ManagerCopilotSession.Status.ACTIVE
        session.last_intent = context_snapshot["intent"]
        session.last_query = query
        session.current_context = context_snapshot
        session.message_count = session.messages.count()
        session.save(
            update_fields=[
                "title",
                "status",
                "last_intent",
                "last_query",
                "current_context",
                "message_count",
                "last_activity_at",
                "updated_at",
            ]
        )
        if response_payload["action_links"]:
            SystemEventService.log_system_event(
                event_type="copilot.manager.action.suggested",
                source_module="ai_agents_center",
                message="Manager copilot suggested actions.",
                entity_type="manager_copilot_session",
                entity_id=str(session.public_id),
                user=user,
                company=company,
                site=site,
                payload={"request_id": request_id, "actions": response_payload["action_links"]},
            )
        SystemEventService.log_system_event(
            event_type="copilot.manager.response.generated",
            source_module="ai_agents_center",
            message="Manager copilot response generated.",
            entity_type="manager_copilot_session",
            entity_id=str(session.public_id),
            user=user,
            company=company,
            site=site,
            payload={
                "request_id": request_id,
                "intent": context_snapshot["intent"],
                "agents_consulted": referenced_agents,
                "recommendation_count": len(recommendations),
                "proposal_count": len(proposals),
            },
        )
        return {
            "session": session,
            "context": context_snapshot,
            "response": response_payload,
            "suggestions": cls.get_suggestions(tenant_context=tenant_context, session=session),
            "messages": list(session.messages.order_by("created_at")[:20]),
        }

    @classmethod
    def get_suggestions(cls, *, tenant_context, session=None):
        company = tenant_context.get("company")
        site = tenant_context.get("site")
        configuration = cls.get_configuration(company=company)
        suggestions = list(configuration.default_suggestions if configuration and configuration.default_suggestions else cls.DEFAULT_SUGGESTIONS)
        if site is not None:
            suggestions.insert(0, f"Resuma a situacao da unidade {site.name} nesta semana.")
            suggestions.insert(1, f"Quais ativos estao mais problematicos em {site.name}?")
        if session and session.current_context.get("contract_label"):
            suggestions.insert(0, f"Tem risco economico no contrato {session.current_context['contract_label']}?")
        if session and session.current_context.get("asset_label"):
            suggestions.insert(0, f"Explique as recomendacoes para {session.current_context['asset_label']}.")
        deduped = []
        seen = set()
        for suggestion in suggestions:
            if suggestion in seen:
                continue
            seen.add(suggestion)
            deduped.append(suggestion)
        return deduped[:8]

    @classmethod
    def get_current_context_payload(cls, *, user, tenant_context, session_public_id=None, context_seed=None):
        session = cls.get_or_create_session(user=user, tenant_context=tenant_context, session_public_id=session_public_id)
        context = session.current_context or cls.resolve_current_context(
            user=user,
            tenant_context=tenant_context,
            query="",
            session=session,
            context_seed=context_seed,
        )
        if context_seed:
            context = cls.resolve_current_context(
                user=user,
                tenant_context=tenant_context,
                query="",
                session=session,
                context_seed=context_seed,
            )
        return {
            "session": session,
            "context": context,
            "suggestions": cls.get_suggestions(tenant_context=tenant_context, session=session),
        }

    @classmethod
    def list_relevant_recommendations(cls, *, user, tenant_context, session_public_id=None):
        session = cls.get_or_create_session(user=user, tenant_context=tenant_context, session_public_id=session_public_id)
        company = tenant_context.get("company")
        return cls.aggregate_recommendations(company=company, context=session.current_context or {})

    @classmethod
    @transaction.atomic
    def reset_session(cls, *, session, user):
        ManagerCopilotMessage.objects.create(
            session=session,
            role=ManagerCopilotMessage.Role.SYSTEM,
            content="Sessao resetada pelo gestor.",
            structured_payload={"event": "reset"},
        )
        session.current_context = {}
        session.last_intent = ""
        session.last_query = ""
        session.status = ManagerCopilotSession.Status.RESET
        session.message_count = session.messages.count()
        session.save(update_fields=["current_context", "last_intent", "last_query", "status", "message_count", "last_activity_at", "updated_at"])
        return session
