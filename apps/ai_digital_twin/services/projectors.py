from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from apps.ai_agents_center.models import AgentAnomalyAttentionFlag, AgentAssetAttentionFlag, AgentRecommendation
from apps.ai_decision_engine.models import AgentDecision
from apps.integration_bus.models import IntegrationEvent
from apps.smart_system.models import Asset, FailureEvent, MaintenancePlan, ServiceOrder, ServiceOrderChecklistResponse, StockMovement


RISK_SCORES = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _bounded_risk(score: int) -> str:
    if score >= 9:
        return "critical"
    if score >= 6:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def _status_for_risk(risk_level: str) -> str:
    return {
        "low": "active",
        "medium": "attention",
        "high": "critical",
        "critical": "critical",
    }.get(risk_level, "active")


def _severity_for_count(count: int, *, medium_threshold: int = 1, high_threshold: int = 3, critical_threshold: int = 5) -> str:
    if count >= critical_threshold:
        return "critical"
    if count >= high_threshold:
        return "high"
    if count >= medium_threshold:
        return "medium"
    return "low"


@dataclass(frozen=True)
class TwinProjectionResult:
    state_payload: dict
    risk_payload: dict
    timeline_payload: list[dict]
    summary_payload: dict
    signals: list[dict]
    risk_level: str
    state_summary: str
    source_window_start: timezone.datetime
    source_window_end: timezone.datetime


class TwinTimelineProjector:
    WINDOW_DAYS = 14

    @classmethod
    def project_for_site(cls, *, site):
        window_start = timezone.now() - timedelta(days=cls.WINDOW_DAYS)
        timeline = []
        for order in site.service_orders.filter(created_at__gte=window_start).order_by("-created_at")[:8]:
            timeline.append(
                {
                    "type": "service_order",
                    "title": order.order_number,
                    "summary": f"{order.title} • {order.get_status_display()}",
                    "occurred_at": order.updated_at.isoformat(),
                    "href": "/app/smart-system/work-orders/",
                }
            )
        for failure in FailureEvent.objects.filter(asset__operational_site=site, detected_at__gte=window_start).select_related("asset").order_by("-detected_at")[:8]:
            timeline.append(
                {
                    "type": "failure",
                    "title": getattr(failure.asset, "name", "Falha"),
                    "summary": failure.symptom,
                    "occurred_at": failure.detected_at.isoformat(),
                    "href": "/app/smart-system/failures/",
                }
            )
        for recommendation in AgentRecommendation.objects.filter(site=site, created_at__gte=window_start).select_related("agent_run", "agent_run__agent").order_by("-created_at")[:8]:
            timeline.append(
                {
                    "type": "recommendation",
                    "title": recommendation.agent_run.agent.name,
                    "summary": recommendation.title or recommendation.summary,
                    "occurred_at": recommendation.created_at.isoformat(),
                    "href": "/app/ai-agents/recommendations/",
                }
            )
        return sorted(timeline, key=lambda item: item["occurred_at"], reverse=True)[:12]

    @classmethod
    def project_for_asset(cls, *, asset):
        window_start = timezone.now() - timedelta(days=cls.WINDOW_DAYS)
        timeline = []
        for failure in asset.failure_events.filter(detected_at__gte=window_start).order_by("-detected_at")[:6]:
            timeline.append(
                {
                    "type": "failure",
                    "title": failure.get_severity_display(),
                    "summary": failure.symptom,
                    "occurred_at": failure.detected_at.isoformat(),
                    "href": "/app/smart-system/failures/",
                }
            )
        for order in asset.service_orders.filter(created_at__gte=window_start).order_by("-created_at")[:6]:
            timeline.append(
                {
                    "type": "service_order",
                    "title": order.order_number,
                    "summary": f"{order.title} • {order.get_status_display()}",
                    "occurred_at": order.updated_at.isoformat(),
                    "href": "/app/smart-system/work-orders/",
                }
            )
        for event in asset.history_events.filter(occurred_at__gte=window_start).order_by("-occurred_at")[:6]:
            timeline.append(
                {
                    "type": "asset_history",
                    "title": event.title,
                    "summary": event.description,
                    "occurred_at": event.occurred_at.isoformat(),
                    "href": f"/app/smart-system/assets/{asset.asset_tag}/",
                }
            )
        return sorted(timeline, key=lambda item: item["occurred_at"], reverse=True)[:12]


class SiteOperationalTwinProjector:
    LOOKBACK_DAYS = 30

    @classmethod
    def project(cls, *, site) -> TwinProjectionResult:
        window_end = timezone.now()
        window_start = window_end - timedelta(days=cls.LOOKBACK_DAYS)
        assets = site.assets.filter(is_active=True)
        orders = site.service_orders
        failures = FailureEvent.objects.filter(asset__operational_site=site)
        overdue_plans = site.maintenance_plans.filter(is_active=True, next_due_date__lt=timezone.localdate())
        active_asset_flags = AgentAssetAttentionFlag.objects.filter(site=site, status=AgentAssetAttentionFlag.Status.ACTIVE)
        anomaly_flags = AgentAnomalyAttentionFlag.objects.filter(site=site, status=AgentAnomalyAttentionFlag.Status.ACTIVE)
        recommendations = AgentRecommendation.objects.filter(site=site).select_related("agent_run", "agent_run__agent").order_by("-created_at")[:6]
        pending_decisions = AgentDecision.objects.filter(site=site, decision_status__in=[AgentDecision.DecisionStatus.AWAITING_APPROVAL, AgentDecision.DecisionStatus.ESCALATED]).count()

        critical_assets = assets.filter(criticality__in=[Asset.Criticality.HIGH, Asset.Criticality.CRITICAL]).count()
        open_orders = orders.filter(status__in=[ServiceOrder.Status.OPEN, ServiceOrder.Status.SCHEDULED, ServiceOrder.Status.ON_HOLD])
        delayed_orders = open_orders.filter(scheduled_end__lt=window_end)
        recent_failures = failures.filter(detected_at__gte=window_start)
        critical_failures = recent_failures.filter(severity__in=[FailureEvent.Severity.HIGH, FailureEvent.Severity.CRITICAL])
        backlog = open_orders.count()
        sla_risk = delayed_orders.count()

        risk_score = (
            critical_assets
            + backlog
            + (critical_failures.count() * 2)
            + overdue_plans.count()
            + active_asset_flags.filter(risk_level__in=["high", "critical"]).count()
            + anomaly_flags.filter(risk_level__in=["high", "critical"]).count()
        )
        risk_level = _bounded_risk(risk_score)
        state_summary = (
            f"{backlog} OS abertas, {critical_failures.count()} falhas criticas recentes, "
            f"{overdue_plans.count()} preventivas vencidas."
        )
        signals = [
            {
                "signal_type": "backlog_pressure",
                "source_type": "service_order",
                "source_reference": str(site.public_id),
                "severity": _severity_for_count(backlog, medium_threshold=3, high_threshold=6, critical_threshold=10),
                "title": "Backlog operacional",
                "summary": f"{backlog} ordens abertas na unidade.",
                "occurred_at": window_end,
                "signal_payload": {"backlog": backlog},
            },
            {
                "signal_type": "preventive_overdue",
                "source_type": "maintenance_plan",
                "source_reference": str(site.public_id),
                "severity": _severity_for_count(overdue_plans.count(), medium_threshold=1, high_threshold=3, critical_threshold=5),
                "title": "Preventivas vencidas",
                "summary": f"{overdue_plans.count()} preventivas fora da janela.",
                "occurred_at": window_end,
                "signal_payload": {"overdue_preventives": overdue_plans.count()},
            },
        ]
        if critical_failures.exists():
            signals.append(
                {
                    "signal_type": "critical_failure",
                    "source_type": "failure_event",
                    "source_reference": str(critical_failures.first().public_id),
                    "severity": "critical",
                    "title": "Falha critica recente",
                    "summary": critical_failures.first().symptom,
                    "occurred_at": critical_failures.first().detected_at,
                    "signal_payload": {"failure_count_30d": critical_failures.count()},
                }
            )
        for recommendation in recommendations[:3]:
            signals.append(
                {
                    "signal_type": "agent_recommendation",
                    "source_type": "agent_recommendation",
                    "source_reference": str(recommendation.public_id),
                    "severity": recommendation.severity or "medium",
                    "title": recommendation.title or recommendation.agent_run.agent.name,
                    "summary": recommendation.summary,
                    "occurred_at": recommendation.created_at,
                    "signal_payload": {"agent": recommendation.agent_run.agent.slug},
                }
            )

        state_payload = {
            "health_summary": state_summary,
            "operational_status": "attention" if risk_level in {"medium", "high"} else "stable",
            "active_alerts": len([item for item in signals if item["severity"] in {"high", "critical"}]),
            "risk_level": risk_level,
            "pending_actions": pending_decisions,
            "recent_changes": recent_failures.count() + delayed_orders.count(),
            "next_expected_events": [
                {"type": "preventive", "count": site.maintenance_plans.filter(is_active=True, next_due_date__gte=timezone.localdate()).count()},
                {"type": "scheduled_visit", "count": site.scheduled_visits.filter(status__in=["planned", "confirmed"]).count() if hasattr(site, "scheduled_visits") else 0},
            ],
            "assets_total": assets.count(),
            "critical_assets": critical_assets,
            "backlog": backlog,
            "sla_risk": sla_risk,
            "open_orders": open_orders.count(),
            "delayed_orders": delayed_orders.count(),
            "recent_failures": recent_failures.count(),
            "overdue_preventives": overdue_plans.count(),
        }
        risk_payload = {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "critical_assets": critical_assets,
            "critical_failures_30d": critical_failures.count(),
            "backlog": backlog,
            "overdue_preventives": overdue_plans.count(),
            "anomaly_flags": anomaly_flags.count(),
            "attention_flags": active_asset_flags.count(),
            "pending_decisions": pending_decisions,
        }
        summary_payload = {
            "title": site.name,
            "subtitle": getattr(site.maintenance_client, "display_name", ""),
            "status": _status_for_risk(risk_level),
            "top_risks": [
                f"{critical_failures.count()} falhas criticas recentes",
                f"{overdue_plans.count()} preventivas vencidas",
                f"{delayed_orders.count()} OS atrasadas",
            ],
            "recommendations": [
                {
                    "title": recommendation.title,
                    "summary": recommendation.summary,
                    "severity": recommendation.severity,
                }
                for recommendation in recommendations
            ],
        }
        return TwinProjectionResult(
            state_payload=state_payload,
            risk_payload=risk_payload,
            timeline_payload=TwinTimelineProjector.project_for_site(site=site),
            summary_payload=summary_payload,
            signals=signals,
            risk_level=risk_level,
            state_summary=state_summary,
            source_window_start=window_start,
            source_window_end=window_end,
        )


class AssetOperationalTwinProjector:
    LOOKBACK_DAYS = 45

    @classmethod
    def project(cls, *, asset) -> TwinProjectionResult:
        window_end = timezone.now()
        window_start = window_end - timedelta(days=cls.LOOKBACK_DAYS)
        failures = asset.failure_events.filter(detected_at__gte=window_start)
        orders = asset.service_orders.filter(created_at__gte=window_start)
        plans = asset.maintenance_plans.filter(is_active=True)
        overdue_plans = plans.filter(next_due_date__lt=timezone.localdate())
        checklist_nok = ServiceOrderChecklistResponse.objects.filter(service_order__asset=asset, created_at__gte=window_start, response_boolean=False)
        stock_movements = StockMovement.objects.filter(service_order__asset=asset, occurred_at__gte=window_start)
        attention_flag = AgentAssetAttentionFlag.objects.filter(asset=asset, status=AgentAssetAttentionFlag.Status.ACTIVE).order_by("-updated_at").first()
        recommendations = AgentRecommendation.objects.filter(asset=asset).select_related("agent_run", "agent_run__agent").order_by("-created_at")[:5]

        criticality_weight = RISK_SCORES.get(asset.criticality, 1)
        failure_score = failures.filter(severity__in=[FailureEvent.Severity.HIGH, FailureEvent.Severity.CRITICAL]).count() * 2
        overdue_score = overdue_plans.count()
        delayed_orders = orders.filter(status__in=[ServiceOrder.Status.OPEN, ServiceOrder.Status.ON_HOLD], scheduled_end__lt=window_end).count()
        nok_score = checklist_nok.count()
        attention_score = 2 if attention_flag and attention_flag.risk_level in {"high", "critical"} else 0
        risk_score = criticality_weight + failure_score + overdue_score + delayed_orders + nok_score + attention_score
        risk_level = _bounded_risk(risk_score)
        current_failure = failures.order_by("-detected_at").first()
        state_summary = (
            f"{asset.name} em {asset.get_status_display()} com risco {risk_level}. "
            f"{failures.count()} falhas e {overdue_plans.count()} preventivas vencidas no periodo."
        )
        reliability = max(0, 100 - (failures.count() * 8) - (delayed_orders * 5) - (nok_score * 4))
        signals = []
        if current_failure:
            signals.append(
                {
                    "signal_type": "recent_failure",
                    "source_type": "failure_event",
                    "source_reference": str(current_failure.public_id),
                    "severity": current_failure.severity,
                    "title": "Falha recente",
                    "summary": current_failure.symptom,
                    "occurred_at": current_failure.detected_at,
                    "signal_payload": {"downtime_minutes": current_failure.downtime_minutes or 0},
                }
            )
        if overdue_plans.exists():
            signals.append(
                {
                    "signal_type": "preventive_overdue",
                    "source_type": "maintenance_plan",
                    "source_reference": str(overdue_plans.first().public_id),
                    "severity": _severity_for_count(overdue_plans.count(), medium_threshold=1, high_threshold=2, critical_threshold=4),
                    "title": "Preventiva fora do prazo",
                    "summary": f"{overdue_plans.count()} planos vencidos para o ativo.",
                    "occurred_at": window_end,
                    "signal_payload": {"overdue_preventives": overdue_plans.count()},
                }
            )
        if checklist_nok.exists():
            signals.append(
                {
                    "signal_type": "checklist_nok",
                    "source_type": "checklist_response",
                    "source_reference": str(checklist_nok.order_by('-created_at').first().public_id),
                    "severity": _severity_for_count(checklist_nok.count(), medium_threshold=1, high_threshold=2, critical_threshold=3),
                    "title": "Checklist NOK recente",
                    "summary": f"{checklist_nok.count()} respostas NOK recentes.",
                    "occurred_at": checklist_nok.order_by("-created_at").first().created_at,
                    "signal_payload": {"nok_count": checklist_nok.count()},
                }
            )
        for recommendation in recommendations[:3]:
            signals.append(
                {
                    "signal_type": "agent_recommendation",
                    "source_type": "agent_recommendation",
                    "source_reference": str(recommendation.public_id),
                    "severity": recommendation.severity or "medium",
                    "title": recommendation.title or recommendation.agent_run.agent.name,
                    "summary": recommendation.summary,
                    "occurred_at": recommendation.created_at,
                    "signal_payload": {"agent": recommendation.agent_run.agent.slug},
                }
            )

        state_payload = {
            "health_summary": state_summary,
            "operational_status": asset.status,
            "active_alerts": len([item for item in signals if item["severity"] in {"high", "critical"}]),
            "risk_level": risk_level,
            "pending_actions": delayed_orders + overdue_plans.count(),
            "recent_changes": failures.count() + orders.count(),
            "next_expected_events": [{"type": "preventive", "count": plans.filter(next_due_date__gte=timezone.localdate()).count()}],
            "asset_identity": {"asset_tag": asset.asset_tag, "name": asset.name, "category": getattr(asset.category, "name", "")},
            "status": asset.status,
            "criticality": asset.criticality,
            "reliability_index": reliability,
            "recent_failures": failures.count(),
            "recent_orders": orders.count(),
            "recent_checklist_nok": checklist_nok.count(),
            "parts_consumed_count": int(stock_movements.aggregate(total=Sum("quantity"))["total"] or 0),
        }
        risk_payload = {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "criticality_weight": criticality_weight,
            "high_failure_events": failures.filter(severity__in=[FailureEvent.Severity.HIGH, FailureEvent.Severity.CRITICAL]).count(),
            "overdue_preventives": overdue_plans.count(),
            "delayed_orders": delayed_orders,
            "checklist_nok": checklist_nok.count(),
            "reliability_index": reliability,
        }
        summary_payload = {
            "title": asset.name,
            "subtitle": asset.asset_tag,
            "status": _status_for_risk(risk_level),
            "top_risks": [
                f"{failures.count()} falhas no periodo",
                f"{overdue_plans.count()} preventivas vencidas",
                f"{checklist_nok.count()} checklist NOK",
            ],
            "maintenance_agent_recommendations": [
                {"title": recommendation.title, "summary": recommendation.summary, "severity": recommendation.severity}
                for recommendation in recommendations
            ],
        }
        return TwinProjectionResult(
            state_payload=state_payload,
            risk_payload=risk_payload,
            timeline_payload=TwinTimelineProjector.project_for_asset(asset=asset),
            summary_payload=summary_payload,
            signals=signals,
            risk_level=risk_level,
            state_summary=state_summary,
            source_window_start=window_start,
            source_window_end=window_end,
        )

