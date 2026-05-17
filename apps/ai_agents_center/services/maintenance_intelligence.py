from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.analytics_platform.models import AnalyticsSnapshot, OperationalMetrics
from apps.observability_center.services.observability_service import SystemEventService
from apps.reporting_center.models import ReportRequest
from apps.smart_system.models import Asset, FailureEvent, MaintenancePlan, ServiceDocument, ServiceOrder, ServiceOrderChecklistResponse


@dataclass
class MaintenanceRecommendationDraft:
    recommendation_type: str
    severity: str
    priority: str
    title: str
    summary: str
    explanation: str
    evidence_summary: str
    suggested_action: str
    attention_score: int
    entity_type: str
    entity_id: str
    payload: dict
    requires_human_approval: bool = True


@dataclass
class MaintenanceActionProposalDraft:
    action_type: str
    target_entity: str
    target_entity_id: str
    title: str
    summary: str
    proposed_payload: dict
    priority: str = "medium"
    approval_required: bool = True


class MaintenanceIntelligenceService:
    DEFAULT_THRESHOLDS = {
        "recurring_failure_window_days": 45,
        "recurring_failure_count": 3,
        "critical_overdue_days": 7,
        "checklist_consecutive_nok": 2,
        "intervention_spike_min_current": 3,
        "intervention_spike_multiplier": 1.5,
        "mtbf_drop_ratio": 0.2,
        "max_mttr_hours_attention": 8,
        "critical_attention_score": 85,
        "high_attention_score": 70,
        "preventive_adherence_warning": 0.8,
        "preventive_adherence_critical": 0.6,
        "downtime_attention_minutes": 480,
    }

    @classmethod
    def get_thresholds(cls, definition) -> dict:
        config = getattr(definition, "config", {}) or {}
        heuristic_overrides = config.get("heuristics", {})
        return {**cls.DEFAULT_THRESHOLDS, **heuristic_overrides}

    @classmethod
    def build_scope_context(
        cls,
        *,
        company,
        site=None,
        asset=None,
        category=None,
        trigger_reference="",
        triggered_by=None,
        definition=None,
    ) -> dict:
        if company is None:
            raise ValueError("Maintenance agent requires a company context.")

        thresholds = cls.get_thresholds(definition)
        assets_queryset = Asset.objects.filter(
            operational_site__maintenance_client__company=company,
            is_active=True,
        ).select_related("operational_site", "category")
        if site is not None:
            assets_queryset = assets_queryset.filter(operational_site=site)
        if asset is not None:
            assets_queryset = assets_queryset.filter(pk=asset.pk)
        if category is not None:
            assets_queryset = assets_queryset.filter(category=category)

        assets = list(assets_queryset.order_by("asset_tag"))
        asset_contexts = [cls.build_asset_context(asset=item, thresholds=thresholds) for item in assets]

        return {
            "company_id": company.id,
            "company_slug": company.slug,
            "site_id": getattr(site, "id", None),
            "site_code": getattr(site, "code", ""),
            "asset_id": getattr(asset, "id", None),
            "category_id": getattr(category, "id", None),
            "category_slug": getattr(category, "slug", ""),
            "trigger_reference": trigger_reference,
            "triggered_by": getattr(triggered_by, "id", None),
            "thresholds": thresholds,
            "asset_count": len(asset_contexts),
            "assets": asset_contexts,
            "site_summary": cls.build_site_summary(asset_contexts=asset_contexts, company=company, site=site),
            "category_summary": cls.build_category_summary(asset_contexts=asset_contexts),
            "analytics": cls.query_analytics(company=company),
        }

    @classmethod
    def build_asset_context(cls, *, asset, thresholds: dict) -> dict:
        now = timezone.now()
        today = timezone.localdate()
        recurring_window_start = now - timedelta(days=thresholds["recurring_failure_window_days"])
        previous_window_start = recurring_window_start - timedelta(days=thresholds["recurring_failure_window_days"])

        failures = list(asset.failure_events.order_by("-detected_at")[:12])
        recent_failures = [failure for failure in failures if failure.detected_at >= recurring_window_start]
        previous_failures = [
            failure
            for failure in asset.failure_events.filter(
                detected_at__gte=previous_window_start,
                detected_at__lt=recurring_window_start,
            ).order_by("-detected_at")[:12]
        ]

        work_orders = list(asset.service_orders.order_by("-opened_at")[:12])
        recent_work_orders = [order for order in work_orders if order.opened_at >= recurring_window_start]
        previous_work_orders = [
            order
            for order in asset.service_orders.filter(
                opened_at__gte=previous_window_start,
                opened_at__lt=recurring_window_start,
            ).order_by("-opened_at")[:12]
        ]

        maintenance_plans = list(asset.maintenance_plans.filter(is_active=True).order_by("next_due_date", "name"))
        overdue_plans = [
            plan
            for plan in maintenance_plans
            if plan.next_due_date and plan.next_due_date < today
        ]
        on_time_plans = [
            plan
            for plan in maintenance_plans
            if not plan.next_due_date or plan.next_due_date >= today
        ]

        checklist_responses = list(
            ServiceOrderChecklistResponse.objects.filter(service_order__asset=asset)
            .select_related("service_order", "checklist_item", "service_order__operational_site")
            .order_by("-service_order__opened_at", "-created_at")[:20]
        )
        nok_responses = [response for response in checklist_responses if cls._response_is_nok(response)]
        recent_nok_orders = []
        for response in checklist_responses:
            if response.service_order_id not in recent_nok_orders and cls._service_order_has_nok(response.service_order):
                recent_nok_orders.append(response.service_order_id)
        recent_reports = list(
            ServiceDocument.objects.filter(service_order__asset=asset, document_type=ServiceDocument.DocumentType.REPORT)
            .select_related("service_order")
            .order_by("-created_at")[:5]
        )
        reporting_requests = list(
            ReportRequest.objects.filter(
                requested_for_company=asset.operational_site.maintenance_client.company,
                source_module="smart_system",
                filters_json__asset_id=str(asset.id),
            ).order_by("-created_at")[:3]
        )

        failure_modes = Counter(
            cls._normalize_failure_mode(failure)
            for failure in recent_failures
            if cls._normalize_failure_mode(failure)
        )
        dominant_failure_mode, dominant_failure_mode_count = ("", 0)
        if failure_modes:
            dominant_failure_mode, dominant_failure_mode_count = failure_modes.most_common(1)[0]

        total_downtime = sum(failure.downtime_minutes or 0 for failure in recent_failures)
        mtbf_hours = cls._calculate_mtbf(recent_failures, recurring_window_start, now)
        previous_mtbf_hours = cls._calculate_mtbf(previous_failures, previous_window_start, recurring_window_start)
        mttr_hours = cls._calculate_mttr(recent_failures)
        availability = cls._calculate_availability(total_downtime, recurring_window_start, now)
        preventive_adherence = round(len(on_time_plans) / len(maintenance_plans), 4) if maintenance_plans else 1.0

        analytics_snapshot = AnalyticsSnapshot.objects.filter(
            snapshot_type__startswith=f"executive_company:{asset.operational_site.maintenance_client.company.slug}",
        ).order_by("-snapshot_date", "-created_at").first()

        return {
            "asset_id": asset.id,
            "asset_public_id": str(asset.public_id),
            "asset_tag": asset.asset_tag,
            "name": asset.name,
            "category": asset.category.name,
            "category_slug": asset.category.slug,
            "site_id": asset.operational_site_id,
            "site_name": asset.operational_site.name,
            "site_code": asset.operational_site.code,
            "status": asset.status,
            "criticality": asset.criticality,
            "recent_failures_count": len(recent_failures),
            "previous_failures_count": len(previous_failures),
            "recent_interventions_count": len(recent_work_orders),
            "previous_interventions_count": len(previous_work_orders),
            "open_work_orders_count": sum(1 for order in work_orders if order.status in {ServiceOrder.Status.OPEN, ServiceOrder.Status.IN_PROGRESS, ServiceOrder.Status.ON_HOLD, ServiceOrder.Status.WAITING_PARTS, ServiceOrder.Status.WAITING_QUOTE_APPROVAL}),
            "corrective_work_orders_count": sum(1 for order in recent_work_orders if order.maintenance_type == ServiceOrder.MaintenanceType.CORRECTIVE),
            "inspection_work_orders_count": sum(1 for order in recent_work_orders if order.maintenance_type == ServiceOrder.MaintenanceType.INSPECTION),
            "preventive_work_orders_count": sum(1 for order in recent_work_orders if order.maintenance_type == ServiceOrder.MaintenanceType.PREVENTIVE),
            "maintenance_plan_count": len(maintenance_plans),
            "overdue_plan_count": len(overdue_plans),
            "preventive_adherence": preventive_adherence,
            "recent_nok_count": len(nok_responses),
            "recent_nok_order_count": len(recent_nok_orders[: thresholds["checklist_consecutive_nok"] + 2]),
            "dominant_failure_mode": dominant_failure_mode,
            "dominant_failure_mode_count": dominant_failure_mode_count,
            "total_downtime_minutes": total_downtime,
            "mtbf_hours": mtbf_hours,
            "previous_mtbf_hours": previous_mtbf_hours,
            "mttr_hours": mttr_hours,
            "availability": availability,
            "recent_failures": [
                {
                    "id": failure.id,
                    "public_id": str(failure.public_id),
                    "detected_at": failure.detected_at.isoformat(),
                    "symptom": failure.symptom,
                    "severity": failure.severity,
                    "downtime_minutes": failure.downtime_minutes or 0,
                    "root_cause": failure.root_cause,
                }
                for failure in recent_failures[:5]
            ],
            "recent_work_orders": [
                {
                    "id": order.id,
                    "public_id": str(order.public_id),
                    "order_number": order.order_number,
                    "maintenance_type": order.maintenance_type,
                    "status": order.status,
                    "opened_at": order.opened_at.isoformat(),
                    "title": order.title,
                }
                for order in work_orders[:5]
            ],
            "preventive_plans": [
                {
                    "id": plan.id,
                    "public_id": str(plan.public_id),
                    "name": plan.name,
                    "frequency_type": plan.frequency_type,
                    "frequency_value": plan.frequency_value,
                    "next_due_date": plan.next_due_date.isoformat() if plan.next_due_date else "",
                    "overdue": bool(plan.next_due_date and plan.next_due_date < today),
                }
                for plan in maintenance_plans[:5]
            ],
            "recent_reports": [
                {
                    "id": report.id,
                    "public_id": str(report.public_id),
                    "title": report.title,
                    "created_at": report.created_at.isoformat(),
                }
                for report in recent_reports
            ],
            "recent_reporting_requests": [
                {
                    "id": request.id,
                    "public_id": str(request.public_id),
                    "status": request.status,
                    "created_at": request.created_at.isoformat(),
                }
                for request in reporting_requests
            ],
            "analytics_snapshot": getattr(analytics_snapshot, "data_json", {}) or {},
        }

    @classmethod
    def analyze_scope(cls, *, context: dict, run=None, definition=None) -> tuple[list[MaintenanceRecommendationDraft], list[MaintenanceActionProposalDraft], list[dict], str]:
        thresholds = context["thresholds"]
        recommendations: list[MaintenanceRecommendationDraft] = []
        proposals: list[MaintenanceActionProposalDraft] = []
        attention_flags: list[dict] = []

        for asset_context in context["assets"]:
            asset_recommendations, asset_proposals, attention_flag = cls.analyze_asset_context(
                asset_context=asset_context,
                thresholds=thresholds,
            )
            recommendations.extend(asset_recommendations)
            proposals.extend(asset_proposals)
            if attention_flag is not None:
                attention_flags.append(attention_flag)

            for recommendation in asset_recommendations:
                cls._log_pattern(
                    event_type="agent.maintenance.pattern.detected",
                    company_id=context["company_id"],
                    site_id=asset_context["site_id"],
                    asset_id=asset_context["asset_id"],
                    payload={"recommendation_type": recommendation.recommendation_type, "attention_score": recommendation.attention_score},
                )

        recommendations.sort(key=lambda item: (item.attention_score, cls._severity_rank(item.severity), cls._priority_rank(item.priority)), reverse=True)
        proposals.sort(key=lambda item: (cls._priority_rank(item.priority), item.action_type), reverse=True)

        scope_label = context.get("site_code") or context.get("category_slug") or "company"
        summary = f"Maintenance intelligence completed for {scope_label}: {len(recommendations)} recommendations and {len(proposals)} proposals."
        return recommendations, proposals, attention_flags, summary

    @classmethod
    def analyze_asset_context(cls, *, asset_context: dict, thresholds: dict) -> tuple[list[MaintenanceRecommendationDraft], list[MaintenanceActionProposalDraft], dict | None]:
        recommendations: list[MaintenanceRecommendationDraft] = []
        proposals: list[MaintenanceActionProposalDraft] = []
        signals: list[str] = []
        asset_id = asset_context["asset_public_id"]
        asset_label = asset_context["asset_tag"]

        if asset_context["recent_failures_count"] >= thresholds["recurring_failure_count"]:
            signals.append("recurring_failures")
            summary = (
                f"Ativo {asset_label} registrou {asset_context['recent_failures_count']} falhas nos ultimos "
                f"{thresholds['recurring_failure_window_days']} dias."
            )
            explanation = "O volume recente de falhas indica reincidencia operacional acima do limite configurado."
            evidence = cls._build_evidence(asset_context, extra=[f"modo dominante: {asset_context['dominant_failure_mode'] or 'sem padrao fechado'}"])
            recommendations.append(
                MaintenanceRecommendationDraft(
                    recommendation_type="failure_pattern_alert",
                    severity="high" if asset_context["criticality"] in {"high", "critical"} else "medium",
                    priority="high",
                    title=f"Padrao recorrente de falhas em {asset_label}",
                    summary=summary,
                    explanation=explanation,
                    evidence_summary=evidence,
                    suggested_action="Revisar causa raiz, consolidar historico tecnico e abrir inspecao extraordinaria.",
                    attention_score=78 if asset_context["criticality"] == "critical" else 68,
                    entity_type="asset",
                    entity_id=asset_id,
                    payload={"signals": ["recurring_failures"], "asset": asset_context},
                )
            )
            proposals.append(
                MaintenanceActionProposalDraft(
                    action_type="open_inspection_work_order",
                    target_entity="asset",
                    target_entity_id=asset_id,
                    title=f"Abrir OS de inspecao para {asset_label}",
                    summary="Inspecao extraordinaria recomendada por reincidencia de falhas.",
                    proposed_payload={"maintenance_type": "inspection", "reason": "recurring_failures", "asset_public_id": asset_id},
                    priority="high",
                )
            )

        if asset_context["dominant_failure_mode_count"] >= thresholds["recurring_failure_count"]:
            signals.append("same_failure_mode")
            recommendations.append(
                MaintenanceRecommendationDraft(
                    recommendation_type="reliability_attention",
                    severity="high",
                    priority="high",
                    title=f"Modo de falha repetido em {asset_label}",
                    summary=f"{asset_label} repete o modo de falha {asset_context['dominant_failure_mode']} sem estabilizacao sustentada.",
                    explanation="A repeticao do mesmo modo de falha sinaliza plano atual insuficiente ou RCA inconclusiva.",
                    evidence_summary=cls._build_evidence(asset_context, extra=[f"modo recorrente: {asset_context['dominant_failure_mode']}"]),
                    suggested_action="Aprofundar analise tecnica e revisar tarefas preventivas associadas ao modo de falha.",
                    attention_score=74,
                    entity_type="asset",
                    entity_id=asset_id,
                    payload={"signals": ["same_failure_mode"], "dominant_failure_mode": asset_context["dominant_failure_mode"]},
                )
            )
            proposals.append(
                MaintenanceActionProposalDraft(
                    action_type="create_technical_analysis",
                    target_entity="asset",
                    target_entity_id=asset_id,
                    title=f"Criar analise tecnica pendente para {asset_label}",
                    summary="Falha repetida sem eliminacao definitiva requer aprofundamento de engenharia.",
                    proposed_payload={"reason": "same_failure_mode", "failure_mode": asset_context["dominant_failure_mode"], "asset_public_id": asset_id},
                    priority="high",
                )
            )

        critical_with_preventive_gap = (
            asset_context["criticality"] in {"high", "critical"}
            and asset_context["overdue_plan_count"] > 0
            and asset_context["preventive_adherence"] <= thresholds["preventive_adherence_warning"]
        )
        if critical_with_preventive_gap:
            signals.append("critical_preventive_gap")
            overdue_text = f"{asset_context['overdue_plan_count']} preventiva(s) vencida(s)"
            recommendations.append(
                MaintenanceRecommendationDraft(
                    recommendation_type="critical_asset_watch",
                    severity="critical" if asset_context["criticality"] == "critical" else "high",
                    priority="immediate",
                    title=f"Ativo critico com aderencia preventiva baixa: {asset_label}",
                    summary=f"{asset_label} e ativo {asset_context['criticality']} com {overdue_text} e aderencia preventiva de {int(asset_context['preventive_adherence'] * 100)}%.",
                    explanation="Ativos criticos com backlog preventivo acumulado aumentam risco de indisponibilidade e falha operacional.",
                    evidence_summary=cls._build_evidence(asset_context, extra=[overdue_text]),
                    suggested_action="Priorizar inspeção extraordinaria, executar preventivas vencidas e revisar cobertura do plano.",
                    attention_score=95 if asset_context["criticality"] == "critical" else 88,
                    entity_type="asset",
                    entity_id=asset_id,
                    payload={"signals": ["critical_preventive_gap"], "preventive_adherence": asset_context["preventive_adherence"]},
                )
            )
            proposals.append(
                MaintenanceActionProposalDraft(
                    action_type="review_preventive_plan",
                    target_entity="asset",
                    target_entity_id=asset_id,
                    title=f"Revisar plano preventivo de {asset_label}",
                    summary="Plano preventivo precisa de revisao por criticidade alta e baixa aderencia.",
                    proposed_payload={"reason": "critical_preventive_gap", "asset_public_id": asset_id},
                    priority="immediate",
                )
            )

        intervention_spike = (
            asset_context["recent_interventions_count"] >= thresholds["intervention_spike_min_current"]
            and asset_context["recent_interventions_count"] > max(1, int(asset_context["previous_interventions_count"] * thresholds["intervention_spike_multiplier"]))
        )
        if intervention_spike:
            signals.append("intervention_spike")
            recommendations.append(
                MaintenanceRecommendationDraft(
                    recommendation_type="action_plan_recommendation",
                    severity="high" if asset_context["criticality"] in {"high", "critical"} else "medium",
                    priority="high",
                    title=f"Aumento recente de intervencoes em {asset_label}",
                    summary=f"{asset_label} saiu de {asset_context['previous_interventions_count']} para {asset_context['recent_interventions_count']} intervencoes no periodo comparado.",
                    explanation="Aumento de corretivas e inspecoes em curto intervalo e sinal de degradacao operacional.",
                    evidence_summary=cls._build_evidence(asset_context),
                    suggested_action="Rever estrategia de manutencao do ativo e avaliar reforco de inspeções.",
                    attention_score=72,
                    entity_type="asset",
                    entity_id=asset_id,
                    payload={"signals": ["intervention_spike"]},
                )
            )

        consecutive_nok = asset_context["recent_nok_order_count"] >= thresholds["checklist_consecutive_nok"]
        if consecutive_nok:
            signals.append("consecutive_nok")
            recommendations.append(
                MaintenanceRecommendationDraft(
                    recommendation_type="extraordinary_inspection",
                    severity="high" if asset_context["criticality"] in {"high", "critical"} else "medium",
                    priority="high",
                    title=f"Checklists com NOK em sequencia para {asset_label}",
                    summary=f"{asset_label} teve {asset_context['recent_nok_order_count']} ordens recentes com checklist NOK.",
                    explanation="Sequencia de NOK indica persistencia de desvio sem estabilizacao no campo.",
                    evidence_summary=cls._build_evidence(asset_context, extra=[f"itens NOK recentes: {asset_context['recent_nok_count']}"]),
                    suggested_action="Executar inspecao extraordinaria e revisar checklist utilizado no ativo.",
                    attention_score=76,
                    entity_type="asset",
                    entity_id=asset_id,
                    payload={"signals": ["consecutive_nok"]},
                )
            )
            proposals.append(
                MaintenanceActionProposalDraft(
                    action_type="review_checklist_strategy",
                    target_entity="asset",
                    target_entity_id=asset_id,
                    title=f"Revisar checklist do ativo {asset_label}",
                    summary="A sequencia de NOK sugere necessidade de revisar pontos de inspeção e resposta operacional.",
                    proposed_payload={"reason": "consecutive_nok", "asset_public_id": asset_id},
                    priority="high",
                )
            )

        mtbf_deteriorating = (
            asset_context["previous_mtbf_hours"] > 0
            and asset_context["mtbf_hours"] > 0
            and asset_context["mtbf_hours"] < asset_context["previous_mtbf_hours"] * (1 - thresholds["mtbf_drop_ratio"])
        )
        if mtbf_deteriorating:
            signals.append("mtbf_deterioration")
            recommendations.append(
                MaintenanceRecommendationDraft(
                    recommendation_type="reliability_attention",
                    severity="high",
                    priority="high",
                    title=f"Deterioracao de MTBF em {asset_label}",
                    summary=f"O MTBF estimado de {asset_label} caiu de {asset_context['previous_mtbf_hours']:.1f}h para {asset_context['mtbf_hours']:.1f}h.",
                    explanation="Queda de MTBF mostra reducao do intervalo medio entre falhas e piora de confiabilidade.",
                    evidence_summary=cls._build_evidence(asset_context),
                    suggested_action="Priorizar analise de confiabilidade e revisar periodicidade preventiva do ativo.",
                    attention_score=82,
                    entity_type="asset",
                    entity_id=asset_id,
                    payload={"signals": ["mtbf_deterioration"]},
                )
            )

        plan_possibly_insufficient = (
            asset_context["maintenance_plan_count"] > 0
            and asset_context["corrective_work_orders_count"] >= asset_context["preventive_work_orders_count"]
            and asset_context["recent_failures_count"] >= 2
        )
        if plan_possibly_insufficient:
            signals.append("preventive_plan_insufficient")
            recommendations.append(
                MaintenanceRecommendationDraft(
                    recommendation_type="preventive_review",
                    severity="medium" if asset_context["criticality"] == "medium" else "high",
                    priority="high",
                    title=f"Plano preventivo possivelmente insuficiente para {asset_label}",
                    summary=f"{asset_label} manteve corretivas elevadas apesar de {asset_context['maintenance_plan_count']} plano(s) ativo(s).",
                    explanation="A relacao entre corretivas recorrentes e cobertura preventiva atual sugere necessidade de reavaliar frequencia e escopo.",
                    evidence_summary=cls._build_evidence(asset_context),
                    suggested_action="Revisar frequencia, itens de inspeção e tarefas preventivas do ativo.",
                    attention_score=71,
                    entity_type="asset",
                    entity_id=asset_id,
                    payload={"signals": ["preventive_plan_insufficient"]},
                )
            )
            proposals.append(
                MaintenanceActionProposalDraft(
                    action_type="reevaluate_preventive_frequency",
                    target_entity="asset",
                    target_entity_id=asset_id,
                    title=f"Reavaliar periodicidade preventiva de {asset_label}",
                    summary="Plano com corretivas persistentes requer ajuste assistido de periodicidade.",
                    proposed_payload={"reason": "preventive_plan_insufficient", "asset_public_id": asset_id},
                    priority="high",
                )
            )

        unavailability_risk = (
            asset_context["total_downtime_minutes"] >= thresholds["downtime_attention_minutes"]
            or (asset_context["criticality"] == "critical" and len(signals) >= 2)
            or asset_context["mttr_hours"] >= thresholds["max_mttr_hours_attention"]
        )
        if unavailability_risk:
            signals.append("unavailability_risk")
            recommendations.append(
                MaintenanceRecommendationDraft(
                    recommendation_type="critical_asset_watch",
                    severity="critical" if asset_context["criticality"] == "critical" else "high",
                    priority="immediate",
                    title=f"Risco de indisponibilidade para {asset_label}",
                    summary=f"{asset_label} acumula sinais de indisponibilidade com {asset_context['total_downtime_minutes']} min de parada recente.",
                    explanation="Tempo de parada, criticidade e sinais combinados colocam o ativo em observacao reforcada.",
                    evidence_summary=cls._build_evidence(asset_context),
                    suggested_action="Marcar ativo em observacao, priorizar backlog e definir plano de contingencia.",
                    attention_score=92 if asset_context["criticality"] == "critical" else 84,
                    entity_type="asset",
                    entity_id=asset_id,
                    payload={"signals": ["unavailability_risk"], "signal_stack": signals},
                )
            )
            proposals.append(
                MaintenanceActionProposalDraft(
                    action_type="mark_asset_under_watch",
                    target_entity="asset",
                    target_entity_id=asset_id,
                    title=f"Marcar {asset_label} em observacao",
                    summary="Ativo deve entrar em watchlist operacional do Maintenance Intelligence Agent.",
                    proposed_payload={"reason": "unavailability_risk", "asset_public_id": asset_id},
                    priority="immediate",
                )
            )

        if not recommendations:
            return [], [], None

        attention_score = max(item.attention_score for item in recommendations)
        risk_level = "critical" if attention_score >= thresholds["critical_attention_score"] else "high" if attention_score >= thresholds["high_attention_score"] else "medium"
        attention_flag = {
            "asset_public_id": asset_id,
            "summary": recommendations[0].title,
            "attention_score": attention_score,
            "risk_level": risk_level,
            "payload": {
                "signals": signals,
                "current_recommendation": recommendations[0].summary,
                "asset_snapshot": asset_context,
            },
        }
        return recommendations, proposals, attention_flag

    @classmethod
    def build_site_summary(cls, *, asset_contexts: list[dict], company, site=None) -> dict:
        if not asset_contexts:
            return {
                "company_id": company.id,
                "site_id": getattr(site, "id", None),
                "total_assets": 0,
                "critical_assets": 0,
                "assets_with_failures": 0,
                "assets_with_overdue_preventives": 0,
            }

        return {
            "company_id": company.id,
            "site_id": getattr(site, "id", None),
            "total_assets": len(asset_contexts),
            "critical_assets": sum(1 for item in asset_contexts if item["criticality"] == "critical"),
            "assets_with_failures": sum(1 for item in asset_contexts if item["recent_failures_count"] > 0),
            "assets_with_overdue_preventives": sum(1 for item in asset_contexts if item["overdue_plan_count"] > 0),
            "sites_impacted": sorted({item["site_name"] for item in asset_contexts}),
        }

    @classmethod
    def build_category_summary(cls, *, asset_contexts: list[dict]) -> list[dict]:
        category_counter: dict[str, dict] = {}
        for item in asset_contexts:
            entry = category_counter.setdefault(
                item["category_slug"],
                {
                    "category": item["category"],
                    "category_slug": item["category_slug"],
                    "asset_count": 0,
                    "recent_failures_count": 0,
                    "overdue_plan_count": 0,
                    "recent_nok_count": 0,
                },
            )
            entry["asset_count"] += 1
            entry["recent_failures_count"] += item["recent_failures_count"]
            entry["overdue_plan_count"] += item["overdue_plan_count"]
            entry["recent_nok_count"] += item["recent_nok_count"]
        return sorted(category_counter.values(), key=lambda item: (item["recent_failures_count"], item["overdue_plan_count"]), reverse=True)

    @classmethod
    def query_analytics(cls, *, company) -> dict:
        latest_metrics = OperationalMetrics.objects.filter(company=company).order_by("-period_start").first()
        asset_snapshot = AnalyticsSnapshot.objects.filter(
            snapshot_type__startswith=f"executive_company:{company.slug}",
        ).order_by("-snapshot_date", "-created_at").first()
        return {
            "operational_metrics": {
                "period_start": latest_metrics.period_start.isoformat() if latest_metrics else "",
                "period_end": latest_metrics.period_end.isoformat() if latest_metrics else "",
                "total_work_orders": getattr(latest_metrics, "total_work_orders", 0),
                "total_preventives": getattr(latest_metrics, "total_preventives", 0),
                "total_correctives": getattr(latest_metrics, "total_correctives", 0),
                "sla_compliance_rate": float(getattr(latest_metrics, "sla_compliance_rate", 0) or 0),
            },
            "snapshot": getattr(asset_snapshot, "data_json", {}) or {},
        }

    @staticmethod
    def _normalize_failure_mode(failure: FailureEvent) -> str:
        for raw_value in (failure.root_cause, failure.probable_cause, failure.symptom):
            normalized = (raw_value or "").strip().lower()
            if normalized:
                return normalized[:120]
        return ""

    @staticmethod
    def _calculate_mtbf(failures: list[FailureEvent], window_start, window_end) -> float:
        total_hours = max((window_end - window_start).total_seconds() / 3600, 0)
        if not failures:
            return round(total_hours, 2)
        return round(total_hours / max(len(failures), 1), 2)

    @staticmethod
    def _calculate_mttr(failures: list[FailureEvent]) -> float:
        downtime_values = [failure.downtime_minutes or 0 for failure in failures if (failure.downtime_minutes or 0) > 0]
        if not downtime_values:
            return 0.0
        return round((sum(downtime_values) / len(downtime_values)) / 60, 2)

    @staticmethod
    def _calculate_availability(total_downtime_minutes: int, window_start, window_end) -> float:
        total_minutes = max((window_end - window_start).total_seconds() / 60, 1)
        availability = max(0.0, 1 - (total_downtime_minutes / total_minutes))
        return round(availability, 4)

    @staticmethod
    def _response_is_nok(response: ServiceOrderChecklistResponse) -> bool:
        if response.response_boolean is False:
            return True
        if (response.response_text or "").strip().upper() == "NOK":
            return True
        if (response.response_choice or "").strip().upper() == "NOK":
            return True
        return False

    @classmethod
    def _service_order_has_nok(cls, service_order: ServiceOrder) -> bool:
        return service_order.checklist_responses.filter(
            Q(response_boolean=False) | Q(response_text__iexact="NOK") | Q(response_choice__iexact="NOK")
        ).exists()

    @staticmethod
    def _build_evidence(asset_context: dict, extra: list[str] | None = None) -> str:
        evidence = [
            f"falhas recentes: {asset_context['recent_failures_count']}",
            f"OS abertas: {asset_context['open_work_orders_count']}",
            f"preventivas vencidas: {asset_context['overdue_plan_count']}",
            f"checklists NOK: {asset_context['recent_nok_count']}",
            f"MTBF: {asset_context['mtbf_hours']:.1f}h",
            f"MTTR: {asset_context['mttr_hours']:.1f}h",
            f"disponibilidade: {round(asset_context['availability'] * 100, 1)}%",
        ]
        if extra:
            evidence.extend(extra)
        return "; ".join(evidence)

    @staticmethod
    def _severity_rank(value: str) -> int:
        return {"low": 1, "medium": 2, "high": 3, "critical": 4}.get(value, 0)

    @staticmethod
    def _priority_rank(value: str) -> int:
        return {"low": 1, "medium": 2, "high": 3, "immediate": 4}.get(value, 0)

    @staticmethod
    def _log_pattern(*, event_type: str, company_id, site_id, asset_id, payload: dict):
        SystemEventService.log_system_event(
            event_type=event_type,
            source_module="ai_agents_center",
            message="Maintenance intelligence pattern detected.",
            entity_type="asset",
            entity_id=str(asset_id),
            payload={
                "company_id": company_id,
                "site_id": site_id,
                **payload,
            },
        )
