from django.db.models import Avg, Q

from apps.ai_agents_center.models import AIBriefing, AgentActionProposal, AgentAnomalyAttentionFlag, AgentAssetAttentionFlag, AgentMarketplaceRequestFlag, AgentProfitabilityAttentionFlag, AgentRecommendation, AgentRun, AgentScheduleHealthFlag, ManagerCopilotSession
from apps.ai_agents_center.services.dashboard import AgentDashboardService
from apps.ai_agents_center.services.briefing_composer import AIBriefingComposer
from apps.ai_agents_center.services.manager_copilot import ManagerCopilotService
from apps.ai_decision_engine.models import AgentDecision, DecisionPolicy
from apps.ai_autonomous_ops.models import AutonomousExecution, AutonomousExecutionGuard, AutonomousIncident, AutonomousModeConfig
from apps.ai_digital_twin.models import DigitalTwin
from apps.ai_knowledge_graph.models import GraphNode
from apps.ai_knowledge_graph.services.graph import GraphInsightService
from apps.ai_experimentation_framework.models import Experiment, ExperimentAssignment, ExperimentMetric
from apps.ai_policy_studio.models import Policy, PolicyEvaluation, PolicyRule, PolicyScope, PolicySimulationRun, PolicyVersion
from apps.ai_optimization_loop.models import (
    DecisionOutcome,
    FeedbackSignal,
    OptimizationPolicy,
    OptimizationProposal,
    RecommendationOutcome,
    SimulationOutcome,
)
from apps.ai_optimization_loop.services.quality import OptimizationQualityService
from apps.ai_simulation_engine.models import SimulationRun, SimulationType


def get_ai_agents_dashboard_context(*, tenant_context):
    company = tenant_context.get("active_company")
    payload = AgentDashboardService.build_dashboard(company=company)
    payload["has_company_context"] = company is not None
    payload["company"] = company
    return payload


def get_operations_health_context(*, tenant_context):
    company = tenant_context.get("active_company") or tenant_context.get("company")
    operational_agent_slugs = ["maintenance-agent", "scheduling-agent"]

    recommendations = AgentRecommendation.objects.select_related(
        "agent_run",
        "agent_run__agent",
        "company",
        "site",
    ).filter(agent_run__agent__slug__in=operational_agent_slugs)
    proposals = AgentActionProposal.objects.select_related(
        "agent_run",
        "agent_run__agent",
        "agent_run__company",
        "agent_run__site",
    ).filter(agent_run__agent__slug__in=operational_agent_slugs)
    asset_flags = AgentAssetAttentionFlag.objects.select_related(
        "agent",
        "company",
        "site",
        "asset",
        "latest_recommendation",
    ).filter(agent__slug="maintenance-agent")
    schedule_flags = AgentScheduleHealthFlag.objects.select_related(
        "agent",
        "company",
        "site",
        "technician",
        "latest_recommendation",
    ).filter(agent__slug="scheduling-agent")
    runs = AgentRun.objects.select_related("agent", "company", "site", "triggered_by").filter(
        agent__slug__in=operational_agent_slugs
    )

    if company is not None:
        recommendations = recommendations.filter(company=company)
        proposals = proposals.filter(agent_run__company=company)
        asset_flags = asset_flags.filter(company=company)
        schedule_flags = schedule_flags.filter(company=company)
        runs = runs.filter(company=company)

    open_recommendations = recommendations.filter(status=AgentRecommendation.Status.OPEN)
    pending_proposals = proposals.filter(status=AgentActionProposal.Status.PENDING_APPROVAL)
    open_asset_flags = asset_flags.filter(status__in=[AgentAssetAttentionFlag.Status.ACTIVE, AgentAssetAttentionFlag.Status.WATCHING])
    open_schedule_flags = schedule_flags.filter(status__in=[AgentScheduleHealthFlag.Status.ACTIVE, AgentScheduleHealthFlag.Status.WATCHING])

    detected_risks = []
    for recommendation in open_recommendations.order_by("-attention_score", "-created_at")[:6]:
        detected_risks.append(
            {
                "kind": "Recomendação",
                "title": recommendation.title,
                "summary": recommendation.summary,
                "agent": recommendation.agent_run.agent.name,
                "risk": recommendation.severity,
                "created_at": recommendation.created_at,
                "href": "admin-shell:ai-agents-recommendations",
            }
        )
    for proposal in pending_proposals.order_by("-created_at")[:6]:
        detected_risks.append(
            {
                "kind": "Proposta",
                "title": proposal.title or proposal.action_type,
                "summary": proposal.summary,
                "agent": proposal.agent_run.agent.name,
                "risk": proposal.priority,
                "created_at": proposal.created_at,
                "href": "admin-shell:ai-agents-proposals",
            }
        )
    detected_risks.sort(key=lambda item: item["created_at"], reverse=True)

    return {
        "company": company,
        "summary_cards": [
            {"label": "Recomendações pendentes", "value": open_recommendations.count(), "href": "admin-shell:ai-agents-recommendations"},
            {"label": "Propostas aguardando aprovação", "value": pending_proposals.count(), "href": "admin-shell:ai-agents-proposals"},
            {"label": "Flags de atenção abertas", "value": open_asset_flags.count() + open_schedule_flags.count(), "href": "admin-shell:ai-agents-maintenance-health"},
            {"label": "Runs recentes", "value": runs.count(), "href": "admin-shell:ai-agents-runs"},
        ],
        "detected_risks": detected_risks[:10],
        "open_asset_flags": list(open_asset_flags.order_by("-attention_score", "-updated_at")[:8]),
        "open_schedule_flags": list(open_schedule_flags.order_by("-attention_score", "-updated_at")[:8]),
        "recent_runs": list(runs.order_by("-created_at")[:8]),
        "quick_links": [
            {"label": "Recomendações", "href": "admin-shell:ai-agents-recommendations"},
            {"label": "Propostas", "href": "admin-shell:ai-agents-proposals"},
            {"label": "Runs", "href": "admin-shell:ai-agents-runs"},
            {"label": "Maintenance Health", "href": "admin-shell:ai-agents-maintenance-health"},
            {"label": "Scheduling Health", "href": "admin-shell:ai-agents-scheduling-health"},
        ],
    }


def get_ai_agents_recommendations_context(*, tenant_context):
    company = tenant_context.get("active_company")
    queryset = AgentRecommendation.objects.select_related("agent_run", "agent_run__agent", "company", "site").order_by("-created_at")
    if company is not None:
        queryset = queryset.filter(company=company)
    return {
        "company": company,
        "recommendations": list(queryset[:50]),
    }


def get_ai_agents_maintenance_health_context(*, tenant_context):
    company = tenant_context.get("active_company")
    queryset = AgentAssetAttentionFlag.objects.select_related(
        "asset",
        "asset__category",
        "site",
        "latest_recommendation",
        "latest_recommendation__agent_run",
        "latest_recommendation__agent_run__agent",
    ).filter(agent__slug="maintenance-agent").order_by("-attention_score", "-updated_at")
    if company is not None:
        queryset = queryset.filter(company=company)
    return {
        "company": company,
        "attention_assets": list(queryset[:50]),
    }


def get_ai_agents_scheduling_health_context(*, tenant_context):
    company = tenant_context.get("active_company")
    queryset = AgentScheduleHealthFlag.objects.select_related(
        "technician",
        "site",
        "latest_recommendation",
        "latest_recommendation__agent_run",
        "latest_recommendation__agent_run__agent",
    ).filter(agent__slug="scheduling-agent").order_by("-attention_score", "-updated_at")
    if company is not None:
        queryset = queryset.filter(company=company)
    return {
        "company": company,
        "schedule_health_flags": list(queryset[:50]),
    }


def get_ai_agents_profitability_health_context(*, tenant_context):
    company = tenant_context.get("active_company")
    queryset = AgentProfitabilityAttentionFlag.objects.select_related(
        "site",
        "client",
        "contract",
        "technician",
        "latest_recommendation",
        "latest_recommendation__agent_run",
        "latest_recommendation__agent_run__agent",
    ).filter(agent__slug="profitability-agent").order_by("-attention_score", "-updated_at")
    if company is not None:
        queryset = queryset.filter(company=company)
    return {
        "company": company,
        "profitability_health_flags": list(queryset[:50]),
    }


def get_ai_agents_marketplace_health_context(*, tenant_context):
    company = tenant_context.get("active_company")
    queryset = AgentMarketplaceRequestFlag.objects.select_related(
        "site",
        "service_request",
        "latest_recommendation",
        "latest_recommendation__agent_run",
        "latest_recommendation__agent_run__agent",
    ).filter(agent__slug="marketplace-agent").order_by("-attention_score", "-updated_at")
    if company is not None:
        queryset = queryset.filter(company=company)
    return {
        "company": company,
        "marketplace_health_flags": list(queryset[:50]),
    }


def get_ai_agents_anomaly_health_context(*, tenant_context):
    company = tenant_context.get("active_company")
    queryset = AgentAnomalyAttentionFlag.objects.select_related(
        "site",
        "asset",
        "client",
        "contract",
        "technician",
        "part",
        "latest_recommendation",
        "latest_recommendation__agent_run",
        "latest_recommendation__agent_run__agent",
    ).filter(agent__slug="anomaly-agent").order_by("-attention_score", "-updated_at")
    if company is not None:
        queryset = queryset.filter(company=company)
    return {
        "company": company,
        "anomaly_health_flags": list(queryset[:50]),
    }


def get_ai_agents_runs_context(*, tenant_context):
    company = tenant_context.get("active_company")
    queryset = AgentRun.objects.select_related("agent", "company", "site", "triggered_by").order_by("-created_at")
    if company is not None:
        queryset = queryset.filter(company=company)
    return {
        "company": company,
        "runs": list(queryset[:50]),
    }


def get_ai_agents_proposals_context(*, tenant_context):
    company = tenant_context.get("active_company")
    queryset = AgentDecision.objects.select_related(
        "company",
        "site",
        "policy_applied",
        "decided_by_user",
        "agent_action_proposal",
        "agent_action_proposal__agent_run",
        "agent_action_proposal__agent_run__agent",
    ).prefetch_related("executions").order_by("-created_at")
    if company is not None:
        queryset = queryset.filter(company=company)
    return {
        "company": company,
        "proposals": list(queryset[:50]),
    }


def get_ai_decision_center_context(*, tenant_context):
    company = tenant_context.get("active_company") or tenant_context.get("company")
    site = tenant_context.get("active_site") or tenant_context.get("site")
    decision_queryset = AgentDecision.objects.select_related(
        "company",
        "site",
        "policy_applied",
        "decided_by_user",
        "agent_action_proposal",
        "agent_action_proposal__agent_run",
        "agent_action_proposal__agent_run__agent",
    ).prefetch_related("approvals", "executions").order_by("-created_at")
    policy_queryset = DecisionPolicy.objects.order_by("action_type", "slug")
    if company is not None:
        decision_queryset = decision_queryset.filter(company=company)
    if site is not None:
        decision_queryset = decision_queryset.filter(site=site)
    return {
        "company": company,
        "site": site,
        "pending_decisions": list(
            decision_queryset.filter(
                decision_status__in=[
                    AgentDecision.DecisionStatus.AWAITING_APPROVAL,
                    AgentDecision.DecisionStatus.ESCALATED,
                ]
            )[:25]
        ),
        "recent_decisions": list(decision_queryset[:50]),
        "policies": list(policy_queryset[:25]),
    }


def get_ai_simulation_center_context(*, tenant_context):
    company = tenant_context.get("active_company") or tenant_context.get("company")
    site = tenant_context.get("active_site") or tenant_context.get("site")
    queryset = SimulationRun.objects.select_related(
        "scenario",
        "scenario__simulation_type",
        "scenario__company",
        "scenario__site",
        "decision",
        "result",
    ).order_by("-created_at")
    if company is not None:
        queryset = queryset.filter(scenario__company=company)
    if site is not None:
        queryset = queryset.filter(scenario__site=site)
    return {
        "company": company,
        "site": site,
        "simulation_runs": list(queryset[:50]),
        "simulation_types": list(SimulationType.objects.filter(enabled=True).order_by("slug")),
    }


def get_ai_optimization_center_context(*, tenant_context):
    company = tenant_context.get("active_company") or tenant_context.get("company")
    site = tenant_context.get("active_site") or tenant_context.get("site")
    recommendation_outcomes = RecommendationOutcome.objects.select_related("recommendation", "company", "site").order_by("-measured_at")
    decision_outcomes = DecisionOutcome.objects.select_related("decision", "company", "site").order_by("-measured_at")
    simulation_outcomes = SimulationOutcome.objects.select_related("simulation_run", "simulation_run__scenario", "company", "site").order_by("-measured_at")
    feedbacks = FeedbackSignal.objects.select_related("company", "site", "user").order_by("-created_at")
    proposals = OptimizationProposal.objects.select_related("company", "site", "policy_applied", "approved_by_user").order_by("-created_at")
    if company is not None:
        recommendation_outcomes = recommendation_outcomes.filter(company=company)
        decision_outcomes = decision_outcomes.filter(company=company)
        simulation_outcomes = simulation_outcomes.filter(company=company)
        feedbacks = feedbacks.filter(company=company)
        proposals = proposals.filter(company=company)
    if site is not None:
        recommendation_outcomes = recommendation_outcomes.filter(site=site)
        decision_outcomes = decision_outcomes.filter(site=site)
        simulation_outcomes = simulation_outcomes.filter(site=site)
        feedbacks = feedbacks.filter(site=site)
        proposals = proposals.filter(site=site)
    return {
        "company": company,
        "site": site,
        "optimization_overview": OptimizationQualityService.overview(company=company, site=site),
        "agent_quality_rows": OptimizationQualityService.agent_quality(company=company)[:8],
        "copilot_quality_rows": OptimizationQualityService.copilot_quality(company=company)[:8],
        "recommendation_outcomes": list(recommendation_outcomes[:12]),
        "decision_outcomes": list(decision_outcomes[:12]),
        "simulation_outcomes": list(simulation_outcomes[:12]),
        "feedback_signals": list(feedbacks[:12]),
        "pending_optimization_proposals": list(proposals.filter(status=OptimizationProposal.Status.PENDING_REVIEW)[:12]),
        "recent_optimization_proposals": list(proposals[:12]),
        "optimization_policies": list(OptimizationPolicy.objects.filter(enabled=True).order_by("target_type", "proposal_type")[:12]),
    }


def get_ai_policy_studio_context(*, tenant_context):
    company = tenant_context.get("active_company") or tenant_context.get("company")
    site = tenant_context.get("active_site") or tenant_context.get("site")
    policies = Policy.objects.prefetch_related("scopes", "rules", "versions").order_by("name", "version")
    evaluations = PolicyEvaluation.objects.select_related("policy", "rule", "company", "site").order_by("-evaluated_at")
    simulations = PolicySimulationRun.objects.select_related("policy", "company", "site", "created_by_user").order_by("-created_at")
    if company is not None:
        policies = policies.filter(Q(scopes__company=company) | Q(is_global=True)).distinct()
        evaluations = evaluations.filter(Q(company=company) | Q(company__isnull=True))
        simulations = simulations.filter(Q(company=company) | Q(company__isnull=True))
    if site is not None:
        evaluations = evaluations.filter(Q(site=site) | Q(site__isnull=True))
        simulations = simulations.filter(Q(site=site) | Q(site__isnull=True))
    return {
        "company": company,
        "site": site,
        "policies": list(policies[:20]),
        "policy_rules": list(PolicyRule.objects.select_related("policy").order_by("policy__name", "id")[:30]),
        "policy_scopes": list(PolicyScope.objects.select_related("policy", "company", "site").order_by("policy__name", "priority")[:30]),
        "policy_versions": list(PolicyVersion.objects.select_related("policy", "created_by_user").order_by("-created_at")[:20]),
        "policy_evaluations": list(evaluations[:30]),
        "policy_simulations": list(simulations[:12]),
    }


def get_ai_experimentation_center_context(*, tenant_context):
    company = tenant_context.get("active_company") or tenant_context.get("company")
    site = tenant_context.get("active_site") or tenant_context.get("site")
    experiments = Experiment.objects.select_related("company", "site", "winner_variant", "result").prefetch_related("variants").order_by("-created_at")
    assignments = ExperimentAssignment.objects.select_related("experiment", "variant", "company", "site").order_by("-assigned_at")
    metrics = ExperimentMetric.objects.select_related("experiment", "variant", "company", "site").order_by("-recorded_at")
    if company is not None:
        experiments = experiments.filter(Q(company=company) | Q(company__isnull=True))
        assignments = assignments.filter(Q(company=company) | Q(company__isnull=True))
        metrics = metrics.filter(Q(company=company) | Q(company__isnull=True))
    if site is not None:
        experiments = experiments.filter(Q(site=site) | Q(site__isnull=True))
        assignments = assignments.filter(Q(site=site) | Q(site__isnull=True))
        metrics = metrics.filter(Q(site=site) | Q(site__isnull=True))
    return {
        "company": company,
        "site": site,
        "experiments": list(experiments[:20]),
        "running_experiments": list(experiments.filter(status=Experiment.Status.RUNNING)[:8]),
        "completed_experiments": list(experiments.filter(status__in=[Experiment.Status.COMPLETED, Experiment.Status.PROMOTED])[:8]),
        "recent_assignments": list(assignments[:20]),
        "recent_metrics": list(metrics[:20]),
    }


def get_ai_autonomy_center_context(*, tenant_context):
    company = tenant_context.get("active_company") or tenant_context.get("company")
    site = tenant_context.get("active_site") or tenant_context.get("site")
    configs = AutonomousModeConfig.objects.order_by("company_id", "-updated_at")
    executions = AutonomousExecution.objects.select_related("company", "site", "source_decision", "source_simulation").order_by("-created_at")
    incidents = AutonomousIncident.objects.select_related("company", "site", "autonomous_execution").order_by("-created_at")
    guards = AutonomousExecutionGuard.objects.order_by("company_id", "guard_type", "threshold_key")
    if company is not None:
        configs = configs.filter(Q(company=company) | Q(company__isnull=True))
        executions = executions.filter(Q(company=company) | Q(company__isnull=True))
        incidents = incidents.filter(Q(company=company) | Q(company__isnull=True))
        guards = guards.filter(Q(company=company) | Q(company__isnull=True))
    if site is not None:
        executions = executions.filter(Q(site=site) | Q(site__isnull=True))
        incidents = incidents.filter(Q(site=site) | Q(site__isnull=True))
    return {
        "company": company,
        "site": site,
        "autonomy_configs": list(configs[:8]),
        "autonomy_executions": list(executions[:20]),
        "autonomy_recent_incidents": list(incidents[:12]),
        "autonomy_guards": list(guards[:12]),
        "autonomy_health": {
            "total": executions.count(),
            "success": executions.filter(execution_status=AutonomousExecution.ExecutionStatus.SUCCEEDED).count(),
            "blocked": executions.filter(execution_status=AutonomousExecution.ExecutionStatus.BLOCKED).count(),
            "rollback": executions.filter(rollback_status=AutonomousExecution.RollbackStatus.EXECUTED).count(),
            "avg_confidence": executions.aggregate(avg=Avg("confidence_score"))["avg"] or 0,
        },
    }


def get_ai_manager_copilot_context(*, tenant_context, user, seed_context=None, session_public_id=None):
    company = tenant_context.get("active_company") or tenant_context.get("company")
    site = tenant_context.get("active_site") or tenant_context.get("site")
    resolved_tenant_context = {"company": company, "site": site}
    payload = ManagerCopilotService.get_current_context_payload(
        user=user,
        tenant_context=resolved_tenant_context,
        session_public_id=session_public_id,
        context_seed=seed_context,
    )
    session = payload["session"]
    recent_sessions = ManagerCopilotSession.objects.select_related("company", "site").filter(user=user)
    if company is not None:
        recent_sessions = recent_sessions.filter(company=company)
    recommendation_cards = ManagerCopilotService.list_relevant_recommendations(
        user=user,
        tenant_context=resolved_tenant_context,
        session_public_id=session.public_id,
    )
    decision_queryset = AgentDecision.objects.select_related(
        "company",
        "site",
        "policy_applied",
        "agent_action_proposal",
        "agent_action_proposal__agent_run",
        "agent_action_proposal__agent_run__agent",
    ).order_by("-created_at")
    if company is not None:
        decision_queryset = decision_queryset.filter(company=company)
    if site is not None:
        decision_queryset = decision_queryset.filter(site=site)
    return {
        "company": company,
        "site": site,
        "copilot_session": session,
        "copilot_context": payload["context"],
        "copilot_suggestions": payload["suggestions"],
        "copilot_messages": list(session.messages.order_by("created_at")[:20]),
        "copilot_recent_sessions": list(recent_sessions.order_by("-last_activity_at")[:8]),
        "copilot_recommendation_cards": recommendation_cards[:6],
        "copilot_pending_proposals": list(
            decision_queryset.filter(
                decision_status__in=[
                    AgentDecision.DecisionStatus.AWAITING_APPROVAL,
                    AgentDecision.DecisionStatus.ESCALATED,
                ]
            )[:8]
        ),
        "copilot_recent_simulations": list(
            SimulationRun.objects.select_related("scenario", "scenario__simulation_type", "result")
            .filter(
                scenario__company=company,
                status=SimulationRun.RunStatus.COMPLETED,
            )
            .order_by("-created_at")[:4]
        ) if company is not None else [],
        "copilot_recent_optimization_proposals": list(
            OptimizationProposal.objects.filter(company=company).order_by("-created_at")[:4]
        ) if company is not None else [],
        "copilot_recent_experiments": list(
            Experiment.objects.filter(Q(company=company) | Q(company__isnull=True)).select_related("winner_variant", "result").order_by("-created_at")[:4]
        ) if company is not None else list(Experiment.objects.select_related("winner_variant", "result").order_by("-created_at")[:4]),
        "copilot_twin_cards": list(
            DigitalTwin.objects.filter(company=company).filter(Q(site=site) | Q(site__isnull=True)).order_by("-last_projected_at")[:4]
        ) if company is not None else [],
        "copilot_graph_cards": [
            GraphInsightService.insights_for_entity(company=company, entity_type=node.node_type, entity_public_id=node.source_id)
            for node in GraphNode.objects.filter(company=company).filter(Q(site=site) | Q(site__isnull=True)).order_by("-updated_at")[:3]
        ] if company is not None else [],
        "copilot_seed_context": seed_context or {},
        "copilot_latest_briefing": AIBriefingComposer.latest_for_context(company=company, audience=AIBriefing.Audience.MANAGER, user=user, site=site),
    }


def get_ai_briefings_context(*, tenant_context, user, filters=None):
    company = tenant_context.get("active_company") or tenant_context.get("company")
    queryset = AIBriefingComposer.list_accessible_briefings(user=user, company=company)
    filters = filters or {}
    if filters.get("briefing_type"):
        queryset = queryset.filter(briefing_type=filters["briefing_type"])
    if filters.get("audience"):
        queryset = queryset.filter(audience=filters["audience"])
    return {
        "company": company,
        "briefing_filters": filters,
        "briefings": list(queryset[:50]),
    }
