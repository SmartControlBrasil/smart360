from __future__ import annotations

from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.urls import reverse
from django.utils import timezone

from apps.ai_agents_center.models import (
    AIBriefing,
    AgentAnomalyAttentionFlag,
    AgentAssetAttentionFlag,
    AgentMarketplaceRequestFlag,
    AgentProfitabilityAttentionFlag,
    AgentRecommendation,
    AgentRun,
    AgentScheduleHealthFlag,
)
from apps.ai_agents_center.services.briefing_composer import AIBriefingComposer
from apps.ai_decision_engine.models import AgentDecision
from apps.ai_digital_twin.models import DigitalTwin
from apps.ai_experimentation_framework.models import Experiment
from apps.ai_optimization_loop.models import OptimizationProposal
from apps.ai_policy_studio.models import PolicyEvaluation
from apps.ai_simulation_engine.models import SimulationRun
from apps.analytics_platform.models import OperationalMetrics
from apps.analytics_platform.services.analytics_service import ExecutiveAnalyticsService
from apps.companies.models import Membership, SiteMembership
from apps.marketplace_technicians.models import TechnicianAssignment, TechnicianMatchingRecord, TechnicianProfile, TechnicianServiceRequest
from apps.observability_center.models import ErrorIncident, JobExecutionTrace, SystemEventLog
from apps.smart_system.models import Asset, FailureEvent, MaintenanceContract, ScheduledVisit, ServiceOrder, TechnicianSchedule


RISK_ORDER = {"critical": 4, "high": 3, "warning": 2, "medium": 2, "info": 1, "low": 1}


def _resolve_scope(*, user, tenant_context):
    company = tenant_context.get("active_company") or tenant_context.get("company")
    site = tenant_context.get("active_site") or tenant_context.get("site")
    company_ids = list(Membership.objects.filter(user=user, status=Membership.Status.ACTIVE).values_list("company_id", flat=True))
    site_ids = list(SiteMembership.objects.filter(user=user, status=SiteMembership.Status.ACTIVE).values_list("site_id", flat=True))
    return {
        "company": company,
        "site": site,
        "company_ids": company_ids,
        "site_ids": site_ids,
    }


def _period_options(selected_key: str):
    today = timezone.localdate()
    options = {
        "today": {"label": "Hoje", "date_from": today, "date_to": today},
        "7d": {"label": "7 dias", "date_from": today - timedelta(days=6), "date_to": today},
        "30d": {"label": "30 dias", "date_from": today - timedelta(days=29), "date_to": today},
        "90d": {"label": "90 dias", "date_from": today - timedelta(days=89), "date_to": today},
    }
    resolved_key = selected_key if selected_key in options else "30d"
    payload = options[resolved_key]
    return {
        "key": resolved_key,
        "label": payload["label"],
        "date_from": payload["date_from"],
        "date_to": payload["date_to"],
        "choices": [{"key": key, "label": value["label"], "active": key == resolved_key} for key, value in options.items()],
    }


def _apply_company_site_scope(queryset, *, company_field, site_field, scope):
    company = scope["company"]
    site = scope["site"]
    company_ids = scope["company_ids"]
    site_ids = scope["site_ids"]
    if company is not None:
        queryset = queryset.filter(**{company_field: company})
    elif company_ids:
        queryset = queryset.filter(**{f"{company_field}__in": company_ids})
    if site_field:
        if site is not None:
            queryset = queryset.filter(**{site_field: site})
        elif site_ids:
            queryset = queryset.filter(**{f"{site_field}__in": site_ids})
    return queryset


def _severity_tone(value: str):
    mapping = {
        "critical": "critical",
        "high": "warning",
        "warning": "warning",
        "medium": "warning",
        "info": "neutral",
        "low": "neutral",
    }
    return mapping.get((value or "").lower(), "neutral")


def _decision_url():
    return reverse("admin-shell:ai-decision-center")


def _simulation_url():
    return reverse("admin-shell:ai-simulation-center")


def _recommendations_url():
    return reverse("admin-shell:ai-agents-recommendations")


def _war_room_kpis(*, scope, orders, decisions, marketplace_requests, schedule_cards, anomaly_flags, profitability_flags):
    critical_backlog = orders.filter(status__in=[ServiceOrder.Status.OPEN, ServiceOrder.Status.ON_HOLD], priority=ServiceOrder.Priority.URGENT).count()
    sla_risk = decisions.filter(decision_status__in=[AgentDecision.DecisionStatus.AWAITING_APPROVAL, AgentDecision.DecisionStatus.ESCALATED]).count()
    assets_attention = AgentAssetAttentionFlag.objects.filter(status=AgentAssetAttentionFlag.Status.ACTIVE)
    assets_attention = _apply_company_site_scope(assets_attention, company_field="company", site_field="site", scope=scope)
    overloaded_technicians = sum(1 for item in schedule_cards if item["jobs"] >= 6 or item["conflicts"] > 0)
    return [
        {"label": "Backlog critico", "value": critical_backlog, "meta": "OS urgentes abertas ou on hold", "tone": "critical"},
        {"label": "SLA em risco", "value": sla_risk, "meta": "decisoes e atendimentos sob pressao", "tone": "warning"},
        {"label": "Ativos em atencao", "value": assets_attention.count(), "meta": "flags ativos dos agentes", "tone": "warning"},
        {"label": "Contratos em atencao", "value": profitability_flags.count(), "meta": "margem ou rentabilidade pressionadas", "tone": "warning"},
        {"label": "Requests sem cobertura", "value": marketplace_requests.filter(status__in=[TechnicianServiceRequest.Status.OPEN, TechnicianServiceRequest.Status.MATCHING]).count(), "meta": "fila marketplace aberta", "tone": "warning"},
        {"label": "Decisoes pendentes", "value": decisions.count(), "meta": "propostas aguardando aprovacao", "tone": "critical"},
        {"label": "Anomalias criticas", "value": anomaly_flags.filter(risk_level__in=["high", "critical"]).count(), "meta": "desvios relevantes recentes", "tone": "critical"},
        {"label": "Tecnicos sobrecarregados", "value": overloaded_technicians, "meta": "carga alta ou conflito na agenda", "tone": "warning"},
    ]


def _build_alerts(*, scope, risk_filter, orders, failures, decisions, marketplace_flags, anomaly_flags, profitability_flags, asset_flags):
    alerts = []
    for failure in failures[:5]:
        alerts.append(
            {
                "title": failure.asset.name,
                "summary": failure.symptom,
                "severity": failure.severity,
                "meta": f"Falha {failure.get_status_display()} • {timezone.localtime(failure.detected_at).strftime('%d/%m %H:%M')}",
                "href": reverse("admin-shell:smart-system-failures"),
            }
        )
    for decision in decisions[:5]:
        alerts.append(
            {
                "title": decision.agent_action_proposal.title or decision.normalized_action_type,
                "summary": decision.decision_reason or decision.agent_action_proposal.summary,
                "severity": decision.risk_level,
                "meta": f"Decision Engine • {decision.agent_action_proposal.agent_run.agent.name}",
                "href": _decision_url(),
            }
        )
    for flag in anomaly_flags[:4]:
        alerts.append(
            {
                "title": flag.display_label,
                "summary": flag.summary,
                "severity": flag.risk_level,
                "meta": "Anomaly Detection Agent",
                "href": reverse("admin-shell:ai-agents-anomaly-health"),
            }
        )
    for request_flag in marketplace_flags[:4]:
        alerts.append(
            {
                "title": getattr(request_flag.service_request, "title", "Marketplace gap"),
                "summary": request_flag.summary,
                "severity": request_flag.risk_level,
                "meta": "Marketplace Allocation Agent",
                "href": reverse("admin-shell:marketplace-technicians-requests"),
            }
        )
    for profit_flag in profitability_flags[:4]:
        alerts.append(
            {
                "title": profit_flag.display_label,
                "summary": profit_flag.summary,
                "severity": profit_flag.risk_level,
                "meta": "Profitability Agent",
                "href": reverse("admin-shell:ai-agents-profitability-health"),
            }
        )
    for asset_flag in asset_flags[:4]:
        alerts.append(
            {
                "title": getattr(asset_flag.asset, "name", "Asset em atencao"),
                "summary": asset_flag.summary,
                "severity": asset_flag.risk_level,
                "meta": "Maintenance Intelligence Agent",
                "href": reverse("admin-shell:ai-agents-maintenance-health"),
            }
        )
    filtered = [item for item in alerts if not risk_filter or item["severity"] == risk_filter]
    return sorted(filtered, key=lambda item: RISK_ORDER.get(item["severity"], 0), reverse=True)[:12]


def _recommendations_panel(*, recommendations):
    return [
        {
            "agent": item.agent_run.agent.name,
            "title": item.title,
            "context": item.summary,
            "severity": item.severity,
            "suggested_action": item.suggested_action or item.explanation or "Abrir recomendacao para detalhes.",
            "status": item.status,
            "href": _recommendations_url(),
        }
        for item in recommendations[:10]
    ]


def _decision_queue(*, decisions):
    rows = []
    for decision in decisions[:10]:
        simulation = (decision.explainability_payload or {}).get("simulation", {})
        rows.append(
            {
                "public_id": str(decision.public_id),
                "action": decision.agent_action_proposal.title or decision.normalized_action_type,
                "origin_agent": decision.agent_action_proposal.agent_run.agent.name,
                "impact": simulation.get("summary") or decision.agent_action_proposal.summary,
                "risk": decision.risk_level,
                "policy": getattr(decision.policy_applied, "name", "Sem policy"),
                "status": decision.decision_status,
                "approval_required": decision.requires_human_approval,
                "expected_approver": ", ".join((decision.explainability_payload or {}).get("approval_roles", [])) or "Gestao responsavel",
            }
        )
    return rows


def _simulation_panel(*, simulations):
    rows = []
    for run in simulations[:8]:
        rows.append(
            {
                "title": run.scenario.title,
                "summary": run.result.summary if hasattr(run, "result") else "",
                "impact_score": float(run.result.impact_score) if hasattr(run, "result") else 0,
                "confidence": run.result.confidence_level if hasattr(run, "result") else "",
                "decision_public_id": str(run.decision.public_id) if run.decision_id else "",
                "href": _simulation_url(),
            }
        )
    return rows


def _operational_health(*, orders, failures, asset_flags, schedule_cards, today_visits):
    return {
        "summary": [
            {"label": "OS abertas", "value": orders.filter(status=ServiceOrder.Status.OPEN).count()},
            {"label": "OS atrasadas", "value": orders.filter(status__in=[ServiceOrder.Status.OPEN, ServiceOrder.Status.ON_HOLD], scheduled_end__lt=timezone.now()).count()},
            {"label": "Falhas abertas", "value": failures.filter(status__in=[FailureEvent.Status.OPEN, FailureEvent.Status.ANALYZING]).count()},
            {"label": "Ativos criticos em atencao", "value": asset_flags.filter(risk_level__in=["high", "critical"]).count()},
        ],
        "top_orders": [
            {
                "order_code": item.order_number,
                "asset": getattr(item.asset, "name", "-"),
                "priority": item.priority,
                "status": item.status,
                "href": reverse("admin-shell:smart-system-work-orders"),
            }
            for item in orders.order_by("-opened_at")[:6]
        ],
        "agenda_glance": schedule_cards[:6],
        "visits": today_visits[:6],
    }


def _financial_health(*, company, contracts_attention_count, analytics_payload, profitability_flags):
    kpis = analytics_payload.get("dashboard_cards", [])
    revenue = next((item for item in kpis if "receita" in item.get("label", "").lower()), None)
    margin = next((item for item in kpis if "margem" in item.get("label", "").lower() or "lucro" in item.get("label", "").lower()), None)
    return {
        "headline": [
            {"label": "Contratos em atencao", "value": contracts_attention_count},
            {"label": "Clientes criticos", "value": len(analytics_payload.get("top_clients", [])[:3])},
            {"label": "Receita resumo", "value": revenue.get("value", "-") if revenue else "-"},
            {"label": "Margem resumo", "value": margin.get("value", "-") if margin else "-"},
        ],
        "contracts": analytics_payload.get("top_contracts", [])[:6],
        "alerts": [
            {"title": item.display_label, "summary": item.summary, "risk": item.risk_level, "href": reverse("admin-shell:ai-agents-profitability-health")}
            for item in profitability_flags[:6]
        ],
    }


def _marketplace_panel(*, requests, assignments, matching_records, flags):
    return {
        "summary": [
            {"label": "Requests abertos", "value": requests.filter(status__in=[TechnicianServiceRequest.Status.OPEN, TechnicianServiceRequest.Status.MATCHING]).count()},
            {"label": "Sem candidato viavel", "value": flags.filter(risk_level__in=["high", "critical"]).count()},
            {"label": "Assignments criticos", "value": assignments.filter(assignment_status__in=[TechnicianAssignment.AssignmentStatus.ASSIGNED, TechnicianAssignment.AssignmentStatus.IN_PROGRESS]).count()},
            {"label": "Cobertura media", "value": round(matching_records.aggregate(avg=Avg("match_score"))["avg"] or 0, 1)},
        ],
        "requests": [
            {
                "title": item.title,
                "status": item.status,
                "priority": item.priority,
                "site": getattr(item.related_site, "name", ""),
                "href": reverse("admin-shell:marketplace-technicians-requests"),
            }
            for item in requests.order_by("-created_at")[:6]
        ],
        "gaps": [
            {"title": item.summary, "meta": getattr(item.service_request, "title", ""), "risk": item.risk_level, "href": reverse("admin-shell:ai-agents-marketplace-health")}
            for item in flags[:6]
        ],
    }


def _anomaly_panel(*, anomaly_flags, events):
    return {
        "summary": [
            {"label": "Desvios ativos", "value": anomaly_flags.count()},
            {"label": "Criticos", "value": anomaly_flags.filter(risk_level__in=["high", "critical"]).count()},
            {"label": "Sites em atencao", "value": anomaly_flags.values("site_id").distinct().count()},
            {"label": "Falhas em alta", "value": events.filter(severity__in=[FailureEvent.Severity.HIGH, FailureEvent.Severity.CRITICAL]).count()},
        ],
        "items": [
            {"title": item.display_label, "summary": item.summary, "risk": item.risk_level, "href": reverse("admin-shell:ai-agents-anomaly-health")}
            for item in anomaly_flags[:8]
        ],
    }


def _ai_governance_panel(*, agent_runs, recommendations, pending_decisions, autoexecuted, optimization_proposals, experiments, policy_evaluations):
    return {
        "summary": [
            {"label": "Agentes ativos", "value": agent_runs.values("agent_id").distinct().count()},
            {"label": "Recomendacoes hoje", "value": recommendations.count()},
            {"label": "Propostas pendentes", "value": pending_decisions.count()},
            {"label": "Decisoes autoexecutadas", "value": autoexecuted.count()},
            {"label": "Ajustes sugeridos", "value": optimization_proposals.count()},
            {"label": "Experimentos ativos", "value": experiments.count()},
        ],
        "policies": [
            {
                "action_type": item.action_type,
                "result": item.result,
                "reason": item.reason,
                "evaluated_at": timezone.localtime(item.evaluated_at).strftime("%d/%m %H:%M"),
            }
            for item in policy_evaluations[:5]
        ],
    }


def _digital_twin_panel(*, twins):
    return [
        {
            "title": getattr(item.site, "name", getattr(item.asset, "name", "Twin")),
            "subtitle": item.asset.asset_tag if item.asset_id else getattr(item.site, "code", ""),
            "risk": item.risk_level,
            "summary": item.current_state_summary,
            "href": f"{reverse('admin-shell:ai-digital-twin-center')}?twin={item.public_id}",
        }
        for item in twins[:6]
    ]


def _intelligence_feed(*, events):
    high_value_types = {
        "agent.maintenance.recommendation.created",
        "agent.anomaly.pattern.detected",
        "decision.awaiting_approval",
        "decision.auto_blocked",
        "simulation.run.completed",
        "optimization.proposal.created",
        "variant.promoted",
        "policy.overridden",
        "decision.execution.failed",
        "agent.marketplace.action.proposed",
    }
    rows = []
    for event in events:
        if event.event_type not in high_value_types:
            continue
        rows.append(
            {
                "event_type": event.event_type,
                "title": event.message,
                "meta": f"{event.source_module} • {timezone.localtime(event.created_at).strftime('%d/%m %H:%M')}",
                "severity": event.severity,
                "entity": event.entity_type,
            }
        )
    return rows[:14]


def build_executive_war_room_context(*, user, tenant_context, filters=None):
    filters = filters or {}
    scope = _resolve_scope(user=user, tenant_context=tenant_context)
    period = _period_options(filters.get("period", "30d"))
    risk_filter = filters.get("risk", "")
    domain_filter = filters.get("domain", "")
    company = scope["company"]
    site = scope["site"]
    analytics_payload = get_analytics_payload(user=user, tenant_context=tenant_context)
    schedule_payload = get_schedule_payload(user=user, tenant_context=tenant_context, period=period)
    queries = get_scoped_queries(scope=scope, period=period, domain_filter=domain_filter)

    alerts = _build_alerts(
        scope=scope,
        risk_filter=risk_filter,
        orders=queries["orders"],
        failures=queries["failures"],
        decisions=queries["pending_decisions"],
        marketplace_flags=queries["marketplace_flags"],
        anomaly_flags=queries["anomaly_flags"],
        profitability_flags=queries["profitability_flags"],
        asset_flags=queries["asset_flags"],
    )
    intelligence_feed = _intelligence_feed(events=queries["events"][:60])
    latest_briefing = AIBriefingComposer.latest_for_context(
        company=company,
        audience=AIBriefing.Audience.MANAGER,
        user=user,
        site=site,
    )
    kpis = _war_room_kpis(
        scope=scope,
        orders=queries["orders"],
        decisions=queries["pending_decisions"],
        marketplace_requests=queries["marketplace_requests"],
        schedule_cards=schedule_payload["technician_load_cards"],
        anomaly_flags=queries["anomaly_flags"],
        profitability_flags=queries["profitability_flags"],
    )
    context = {
        "war_room_filters": {
            "period": period,
            "risk": risk_filter,
            "domain": domain_filter,
            "company": getattr(company, "name", "Todas as empresas"),
            "site": getattr(site, "name", "Todas as unidades"),
            "domain_choices": [
                {"key": "", "label": "Todos os dominios", "active": not domain_filter},
                {"key": "maintenance", "label": "Maintenance", "active": domain_filter == "maintenance"},
                {"key": "scheduling", "label": "Scheduling", "active": domain_filter == "scheduling"},
                {"key": "profitability", "label": "Profitability", "active": domain_filter == "profitability"},
                {"key": "marketplace", "label": "Marketplace", "active": domain_filter == "marketplace"},
                {"key": "anomaly", "label": "Anomaly", "active": domain_filter == "anomaly"},
            ],
            "risk_choices": [
                {"key": "", "label": "Todos os riscos", "active": not risk_filter},
                {"key": "critical", "label": "Critical", "active": risk_filter == "critical"},
                {"key": "high", "label": "High", "active": risk_filter == "high"},
                {"key": "medium", "label": "Medium", "active": risk_filter == "medium"},
            ],
        },
        "war_room_kpis": kpis,
        "war_room_alerts": alerts,
        "war_room_recommendations": _recommendations_panel(recommendations=queries["recommendations"]),
        "war_room_decisions": _decision_queue(decisions=queries["pending_decisions"]),
        "war_room_simulations": _simulation_panel(simulations=queries["simulations"]),
        "war_room_operational_health": _operational_health(
            orders=queries["orders"],
            failures=queries["failures"],
            asset_flags=queries["asset_flags"],
            schedule_cards=schedule_payload["technician_load_cards"],
            today_visits=schedule_payload["today_visits"],
        ),
        "war_room_financial_health": _financial_health(
            company=company,
            contracts_attention_count=queries["profitability_flags"].count(),
            analytics_payload=analytics_payload,
            profitability_flags=queries["profitability_flags"],
        ),
        "war_room_field_panel": {
            "summary": [
                {"label": "Tecnicos sobrecarregados", "value": sum(1 for item in schedule_payload["technician_load_cards"] if item["jobs"] >= 6)},
                {"label": "Tecnicos ociosos", "value": sum(1 for item in schedule_payload["technician_load_cards"] if item["jobs"] <= 1)},
                {"label": "Visitas em conflito", "value": len(schedule_payload["conflict_visits"])},
                {"label": "Nao alocadas", "value": len(schedule_payload["unassigned_visits"])},
            ],
            "technicians": schedule_payload["technician_load_cards"][:8],
            "visits": schedule_payload["conflict_visits"][:6] or schedule_payload["unassigned_visits"][:6],
        },
        "war_room_marketplace_panel": _marketplace_panel(
            requests=queries["marketplace_requests"],
            assignments=queries["marketplace_assignments"],
            matching_records=queries["marketplace_matching"],
            flags=queries["marketplace_flags"],
        ),
        "war_room_anomaly_panel": _anomaly_panel(anomaly_flags=queries["anomaly_flags"], events=queries["failures"]),
        "war_room_ai_governance": _ai_governance_panel(
            agent_runs=queries["agent_runs"],
            recommendations=queries["recommendations"],
            pending_decisions=queries["pending_decisions"],
            autoexecuted=queries["autoexecuted_decisions"],
            optimization_proposals=queries["optimization_proposals"],
            experiments=queries["experiments"],
            policy_evaluations=queries["policy_evaluations"],
        ),
        "war_room_twin_hotspots": _digital_twin_panel(twins=queries["digital_twins"]),
        "war_room_intelligence_feed": intelligence_feed,
        "war_room_briefing": latest_briefing,
        "war_room_observability": {
            "incidents_open": queries["incidents"].count(),
            "jobs_failed": queries["failed_jobs"].count(),
            "top_events": intelligence_feed[:6],
        },
        "war_room_quick_actions": [
            {"label": "Abrir decisoes pendentes", "href": _decision_url()},
            {"label": "Rodar simulacoes", "href": _simulation_url()},
            {"label": "Disparar agentes", "href": reverse("admin-shell:ai-agents-runs")},
            {"label": "Abrir Copilot do Gestor", "href": f"{reverse('admin-shell:ai-manager-copilot')}?question=Resuma o war room atual"},
            {"label": "Contratos em risco", "href": reverse("admin-shell:ai-agents-profitability-health")},
            {"label": "Ativos em atencao", "href": reverse("admin-shell:ai-agents-maintenance-health")},
            {"label": "Agenda critica", "href": reverse("admin-shell:smart-system-scheduling")},
            {"label": "Requests sem alocacao", "href": reverse("admin-shell:marketplace-technicians-requests")},
            {"label": "Abrir Digital Twins", "href": reverse("admin-shell:ai-digital-twin-center")},
        ],
        "war_room_api_payload": {
            "kpis": kpis,
            "alerts": alerts[:8],
            "decision_queue_count": len(_decision_queue(decisions=queries["pending_decisions"])),
            "recommendations_count": queries["recommendations"].count(),
            "feed": intelligence_feed[:10],
            "twin_hotspots": _digital_twin_panel(twins=queries["digital_twins"]),
        },
        "war_room_sources": {
            "analytics": analytics_payload,
            "schedule": schedule_payload,
        },
    }
    return context


def get_scoped_queries(*, scope, period, domain_filter=""):
    date_from = period["date_from"]
    company = scope["company"]
    site = scope["site"]
    orders = _apply_company_site_scope(
        ServiceOrder.objects.select_related("client", "operational_site", "asset", "assigned_to"),
        company_field="client__company",
        site_field="operational_site",
        scope=scope,
    ).filter(opened_at__date__gte=date_from)
    failures = _apply_company_site_scope(
        FailureEvent.objects.select_related("asset", "service_order", "asset__operational_site"),
        company_field="asset__operational_site__maintenance_client__company",
        site_field="asset__operational_site",
        scope=scope,
    ).filter(detected_at__date__gte=date_from)
    recommendations = _apply_company_site_scope(
        AgentRecommendation.objects.select_related("agent_run", "agent_run__agent", "company", "site").order_by("-created_at"),
        company_field="company",
        site_field="site",
        scope=scope,
    ).filter(created_at__date__gte=date_from)
    agent_runs = _apply_company_site_scope(
        AgentRun.objects.select_related("agent", "company", "site"),
        company_field="company",
        site_field="site",
        scope=scope,
    ).filter(created_at__date__gte=date_from)
    if domain_filter:
        recommendations = recommendations.filter(agent_run__agent__domain=domain_filter)
        agent_runs = agent_runs.filter(agent__domain=domain_filter)
    pending_decisions = _apply_company_site_scope(
        AgentDecision.objects.select_related("agent_action_proposal", "agent_action_proposal__agent_run", "agent_action_proposal__agent_run__agent", "policy_applied"),
        company_field="company",
        site_field="site",
        scope=scope,
    ).filter(
        decision_status__in=[AgentDecision.DecisionStatus.AWAITING_APPROVAL, AgentDecision.DecisionStatus.ESCALATED],
        created_at__date__gte=date_from,
    ).order_by("-created_at")
    autoexecuted_decisions = _apply_company_site_scope(
        AgentDecision.objects.select_related("company", "site"),
        company_field="company",
        site_field="site",
        scope=scope,
    ).filter(decision_status=AgentDecision.DecisionStatus.EXECUTED, decided_at__date__gte=date_from)
    simulations = _apply_company_site_scope(
        SimulationRun.objects.select_related("scenario", "scenario__simulation_type", "scenario__company", "scenario__site", "result", "decision"),
        company_field="scenario__company",
        site_field="scenario__site",
        scope=scope,
    ).filter(status=SimulationRun.RunStatus.COMPLETED, created_at__date__gte=date_from).order_by("-created_at")
    optimization_proposals = _apply_company_site_scope(
        OptimizationProposal.objects.select_related("company", "site"),
        company_field="company",
        site_field="site",
        scope=scope,
    ).filter(created_at__date__gte=date_from)
    policy_evaluations = _apply_company_site_scope(
        PolicyEvaluation.objects.select_related("policy", "rule", "company", "site"),
        company_field="company",
        site_field="site",
        scope=scope,
    ).filter(evaluated_at__date__gte=date_from).order_by("-evaluated_at")
    digital_twins = _apply_company_site_scope(
        DigitalTwin.objects.select_related("company", "site", "asset").order_by("-last_projected_at"),
        company_field="company",
        site_field="site",
        scope=scope,
    ).filter(last_projected_at__date__gte=date_from)
    experiments = _apply_company_site_scope(
        Experiment.objects.select_related("winner_variant", "result", "company", "site"),
        company_field="company",
        site_field="site",
        scope=scope,
    ).filter(status=Experiment.Status.RUNNING)
    asset_flags = _apply_company_site_scope(
        AgentAssetAttentionFlag.objects.select_related("asset", "company", "site"),
        company_field="company",
        site_field="site",
        scope=scope,
    ).filter(status=AgentAssetAttentionFlag.Status.ACTIVE)
    schedule_flags = _apply_company_site_scope(
        AgentScheduleHealthFlag.objects.select_related("company", "site", "technician"),
        company_field="company",
        site_field="site",
        scope=scope,
    ).filter(status=AgentScheduleHealthFlag.Status.ACTIVE)
    profitability_flags = _apply_company_site_scope(
        AgentProfitabilityAttentionFlag.objects.select_related("company", "site", "client", "contract"),
        company_field="company",
        site_field="site",
        scope=scope,
    ).filter(status=AgentProfitabilityAttentionFlag.Status.ACTIVE)
    marketplace_flags = _apply_company_site_scope(
        AgentMarketplaceRequestFlag.objects.select_related("company", "site", "service_request"),
        company_field="company",
        site_field="site",
        scope=scope,
    ).filter(status=AgentMarketplaceRequestFlag.Status.ACTIVE)
    anomaly_flags = _apply_company_site_scope(
        AgentAnomalyAttentionFlag.objects.select_related("company", "site", "asset", "client", "contract"),
        company_field="company",
        site_field="site",
        scope=scope,
    ).filter(status=AgentAnomalyAttentionFlag.Status.ACTIVE)
    marketplace_requests = _apply_company_site_scope(
        TechnicianServiceRequest.objects.select_related("requester_company", "related_site", "related_asset"),
        company_field="requester_company",
        site_field="related_site",
        scope=scope,
    )
    marketplace_assignments = TechnicianAssignment.objects.select_related("technician_service_request", "technician_profile").filter(
        technician_service_request__in=marketplace_requests
    )
    marketplace_matching = TechnicianMatchingRecord.objects.select_related("technician_service_request", "technician_profile").filter(
        technician_service_request__in=marketplace_requests
    )
    events = _apply_company_site_scope(
        SystemEventLog.objects.select_related("company", "site"),
        company_field="company",
        site_field="site",
        scope=scope,
    ).filter(created_at__date__gte=date_from).order_by("-created_at")
    incidents = _apply_company_site_scope(
        ErrorIncident.objects.select_related("company", "site"),
        company_field="company",
        site_field="site",
        scope=scope,
    ).filter(status=ErrorIncident.Status.OPEN)
    failed_jobs = _apply_company_site_scope(
        JobExecutionTrace.objects.select_related("company", "site"),
        company_field="company",
        site_field="site",
        scope=scope,
    ).filter(status=JobExecutionTrace.Status.FAILED, started_at__date__gte=date_from)
    return {
        "orders": orders,
        "failures": failures,
        "recommendations": recommendations,
        "agent_runs": agent_runs,
        "pending_decisions": pending_decisions,
        "autoexecuted_decisions": autoexecuted_decisions,
        "simulations": simulations,
        "optimization_proposals": optimization_proposals,
        "policy_evaluations": policy_evaluations,
        "digital_twins": digital_twins,
        "experiments": experiments,
        "asset_flags": asset_flags,
        "schedule_flags": schedule_flags,
        "profitability_flags": profitability_flags,
        "marketplace_flags": marketplace_flags,
        "anomaly_flags": anomaly_flags,
        "marketplace_requests": marketplace_requests,
        "marketplace_assignments": marketplace_assignments,
        "marketplace_matching": marketplace_matching,
        "events": events,
        "incidents": incidents,
        "failed_jobs": failed_jobs,
    }


def get_analytics_payload(*, user, tenant_context):
    period_type = OperationalMetrics.PeriodType.MONTHLY
    company = tenant_context.get("active_company") or tenant_context.get("company") or ExecutiveAnalyticsService.resolve_company_scope(user=user)
    if company is None:
        return {"dashboard_cards": [], "top_clients": [], "top_contracts": [], "alerts": []}
    payload = ExecutiveAnalyticsService.build_executive_dashboard(company=company, period_type=period_type)
    return {
        "dashboard_cards": payload["kpis"],
        "top_clients": payload["top_clients"],
        "top_contracts": payload["top_contracts"],
        "alerts": payload["alerts"],
        "sla_summary": payload["sla_summary"],
    }


def get_schedule_payload(*, user, tenant_context, period):
    from apps.admin_shell.services.smart_system_scheduling import get_scheduling_dashboard_context

    target_date = period["date_to"]
    normalized_context = {
        "company": tenant_context.get("active_company") or tenant_context.get("company"),
        "site": tenant_context.get("active_site") or tenant_context.get("site"),
    }
    return get_scheduling_dashboard_context(tenant_context=normalized_context, user=user, date_value=target_date)
