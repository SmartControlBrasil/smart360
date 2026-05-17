from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.access_control_center.models import AccessAuditLog
from apps.access_control_center.services.access_service import AccessAuditService
from apps.ai_agents_center.memory.service import AgentMemoryService
from apps.ai_agents_center.models import (
    AgentActionProposal,
    AgentAnomalyAttentionFlag,
    AgentAssetAttentionFlag,
    AgentMarketplaceRequestFlag,
    AgentProfitabilityAttentionFlag,
    AgentRecommendation,
    AgentRun,
    AgentScheduleHealthFlag,
)
from apps.ai_agents_center.policies.service import AgentPolicyService
from apps.ai_shared.interfaces.decision_engine import get_decision_orchestrator
from apps.ai_agents_center.services.registry import AgentRegistryService
from apps.ai_experimentation_framework.services.engine import ExperimentationEngine
from apps.ai_policy_studio.models import PolicyRule
from apps.ai_policy_studio.services.engine import PolicyStudioEngine
from apps.observability_center.services.observability_service import JobExecutionTraceService, SystemEventService
from shared_kernel.observability.context import get_correlation_id, get_request_id


class AgentCoordinatorService:
    @classmethod
    @transaction.atomic
    def run_agent(
        cls,
        *,
        agent_slug,
        company=None,
        site=None,
        triggered_by=None,
        trigger_type=AgentRun.TriggerType.MANUAL,
        trigger_reference="",
    ):
        agent_definition = AgentRegistryService.get_agent_definition(agent_slug)
        if agent_definition is None:
            raise ValueError("Agent not found.")
        allowed, reason = AgentPolicyService.can_run_agent(
            user=triggered_by,
            company=company,
            agent_definition=agent_definition,
            trigger_type=trigger_type,
        )
        if not allowed:
            raise PermissionError(reason)
        studio_result = PolicyStudioEngine.evaluate(
            module_slug="ai_agents_center",
            action_type="run_agent",
            company=company,
            site=site,
            risk_level="medium",
            autonomy_level=agent_definition.autonomy_level,
            agent_slug=agent_slug,
            context={"trigger_type": trigger_type},
        )
        if not studio_result.allowed:
            raise PermissionError(studio_result.reason)

        trace = JobExecutionTraceService.start_job(
            job_name=f"agent:{agent_slug}",
            source_module="ai_agents_center",
            payload={"company": getattr(company, "slug", ""), "site": getattr(site, "code", "")},
        )
        run = AgentRun.objects.create(
            agent=agent_definition,
            trigger_type=trigger_type,
            trigger_reference=trigger_reference,
            company=company,
            site=site,
            triggered_by=triggered_by,
            status=AgentRun.Status.RUNNING,
            request_id=get_request_id(),
            correlation_id=get_correlation_id(),
            started_at=timezone.now(),
        )
        SystemEventService.log_system_event(
            event_type="agent.run.started",
            source_module="ai_agents_center",
            message=f"Agent run started for {agent_slug}.",
            entity_type="agent_run",
            entity_id=str(run.public_id),
            user=triggered_by,
            company=company,
            site=site,
            payload={"agent": agent_slug, "trigger_type": trigger_type},
        )
        if agent_definition.domain == agent_definition.Domain.MAINTENANCE:
            SystemEventService.log_system_event(
                event_type="agent.maintenance.run.started",
                source_module="ai_agents_center",
                message="Maintenance intelligence run started.",
                entity_type="agent_run",
                entity_id=str(run.public_id),
                user=triggered_by,
                company=company,
                site=site,
                payload={"agent": agent_slug, "trigger_type": trigger_type, "trigger_reference": trigger_reference},
            )
        if agent_definition.domain == agent_definition.Domain.SCHEDULING:
            SystemEventService.log_system_event(
                event_type="agent.scheduling.run.started",
                source_module="ai_agents_center",
                message="Scheduling optimization run started.",
                entity_type="agent_run",
                entity_id=str(run.public_id),
                user=triggered_by,
                company=company,
                site=site,
                payload={"agent": agent_slug, "trigger_type": trigger_type, "trigger_reference": trigger_reference},
            )
        if agent_definition.domain == agent_definition.Domain.PROFITABILITY:
            SystemEventService.log_system_event(
                event_type="agent.profitability.run.started",
                source_module="ai_agents_center",
                message="Profitability analysis run started.",
                entity_type="agent_run",
                entity_id=str(run.public_id),
                user=triggered_by,
                company=company,
                site=site,
                payload={"agent": agent_slug, "trigger_type": trigger_type, "trigger_reference": trigger_reference},
            )
        if agent_definition.domain == agent_definition.Domain.MARKETPLACE:
            SystemEventService.log_system_event(
                event_type="agent.marketplace.run.started",
                source_module="ai_agents_center",
                message="Marketplace allocation run started.",
                entity_type="agent_run",
                entity_id=str(run.public_id),
                user=triggered_by,
                company=company,
                site=site,
                payload={"agent": agent_slug, "trigger_type": trigger_type, "trigger_reference": trigger_reference},
            )
        if agent_definition.domain == agent_definition.Domain.ANOMALY:
            SystemEventService.log_system_event(
                event_type="agent.anomaly.run.started",
                source_module="ai_agents_center",
                message="Anomaly detection run started.",
                entity_type="agent_run",
                entity_id=str(run.public_id),
                user=triggered_by,
                company=company,
                site=site,
                payload={"agent": agent_slug, "trigger_type": trigger_type, "trigger_reference": trigger_reference},
        )
        try:
            agent = AgentRegistryService.instantiate(agent_slug)
            experiment_assignment = ExperimentationEngine.resolve_assignment(
                target_component="agent",
                target_reference=agent_slug,
                entity_key=f"{getattr(company, 'id', 'global')}:{getattr(site, 'id', 'all')}:{trigger_type}:{trigger_reference or run.public_id}",
                entity_type="agent_run",
                company=company,
                site=site,
                context={"agent_slug": agent_slug, "trigger_type": trigger_type},
            )
            context = agent.build_context(
                company=company,
                site=site,
                trigger_reference=trigger_reference,
                triggered_by=triggered_by,
            )
            if experiment_assignment is not None:
                context["experiment"] = {
                    "experiment_public_id": str(experiment_assignment.experiment.public_id),
                    "assignment_public_id": str(experiment_assignment.public_id),
                    "variant_public_id": str(experiment_assignment.variant.public_id),
                    "variant_slug": experiment_assignment.variant.slug,
                    "variant_config": experiment_assignment.variant.config_payload,
                }
            run.input_context = context
            recommendations, proposals, output_summary = agent.generate(context=context)
            run.output_summary = output_summary
            run.status = AgentRun.Status.COMPLETED
            run.finished_at = timezone.now()
            run.duration_ms = max(int((run.finished_at - run.started_at).total_seconds() * 1000), 0)
            run.save(update_fields=["input_context", "output_summary", "status", "finished_at", "duration_ms", "updated_at"])

            created_recommendations = []
            created_proposals = []
            for recommendation in recommendations[: agent_definition.execution_policy.max_recommendations]:
                created_recommendations.append(
                    AgentRecommendation.objects.create(
                        agent_run=run,
                        company=company,
                        site=site,
                        recommendation_type=recommendation.recommendation_type,
                        title=recommendation.title,
                        summary=recommendation.summary,
                        explanation=recommendation.explanation,
                        evidence_summary=recommendation.evidence_summary,
                        suggested_action=recommendation.suggested_action,
                        payload=recommendation.payload,
                        severity=recommendation.severity,
                        priority=recommendation.priority,
                        attention_score=recommendation.attention_score,
                        requires_human_approval=recommendation.requires_human_approval,
                        entity_type=recommendation.entity_type,
                        entity_id=recommendation.entity_id,
                    )
                )
                if agent_definition.domain == agent_definition.Domain.MAINTENANCE:
                    SystemEventService.log_system_event(
                        event_type="agent.maintenance.recommendation.created",
                        source_module="ai_agents_center",
                        message="Maintenance recommendation created.",
                        entity_type=recommendation.entity_type,
                        entity_id=recommendation.entity_id,
                        user=triggered_by,
                        company=company,
                        site=site,
                        payload={
                            "recommendation_type": recommendation.recommendation_type,
                            "severity": recommendation.severity,
                            "priority": recommendation.priority,
                            "attention_score": recommendation.attention_score,
                        },
                    )
                if agent_definition.domain == agent_definition.Domain.SCHEDULING:
                    SystemEventService.log_system_event(
                        event_type="agent.scheduling.recommendation.created",
                        source_module="ai_agents_center",
                        message="Scheduling recommendation created.",
                        entity_type=recommendation.entity_type,
                        entity_id=recommendation.entity_id,
                        user=triggered_by,
                        company=company,
                        site=site,
                        payload={
                            "recommendation_type": recommendation.recommendation_type,
                            "severity": recommendation.severity,
                            "priority": recommendation.priority,
                            "attention_score": recommendation.attention_score,
                        },
                    )
                if agent_definition.domain == agent_definition.Domain.PROFITABILITY:
                    SystemEventService.log_system_event(
                        event_type="agent.profitability.recommendation.created",
                        source_module="ai_agents_center",
                        message="Profitability recommendation created.",
                        entity_type=recommendation.entity_type,
                        entity_id=recommendation.entity_id,
                        user=triggered_by,
                        company=company,
                        site=site,
                        payload={
                            "recommendation_type": recommendation.recommendation_type,
                            "severity": recommendation.severity,
                            "priority": recommendation.priority,
                            "attention_score": recommendation.attention_score,
                        },
                    )
                if agent_definition.domain == agent_definition.Domain.MARKETPLACE:
                    SystemEventService.log_system_event(
                        event_type="agent.marketplace.recommendation.created",
                        source_module="ai_agents_center",
                        message="Marketplace recommendation created.",
                        entity_type=recommendation.entity_type,
                        entity_id=recommendation.entity_id,
                        user=triggered_by,
                        company=company,
                        site=site,
                        payload={
                            "recommendation_type": recommendation.recommendation_type,
                            "severity": recommendation.severity,
                            "priority": recommendation.priority,
                            "attention_score": recommendation.attention_score,
                        },
                    )
                if agent_definition.domain == agent_definition.Domain.ANOMALY:
                    SystemEventService.log_system_event(
                        event_type="agent.anomaly.pattern.detected",
                        source_module="ai_agents_center",
                        message="Anomaly pattern detected.",
                        entity_type=recommendation.entity_type,
                        entity_id=recommendation.entity_id,
                        user=triggered_by,
                        company=company,
                        site=site,
                        payload={
                            "recommendation_type": recommendation.recommendation_type,
                            "severity": recommendation.severity,
                            "priority": recommendation.priority,
                            "attention_score": recommendation.attention_score,
                        },
                    )
                    SystemEventService.log_system_event(
                        event_type="agent.anomaly.recommendation.created",
                        source_module="ai_agents_center",
                        message="Anomaly recommendation created.",
                        entity_type=recommendation.entity_type,
                        entity_id=recommendation.entity_id,
                        user=triggered_by,
                        company=company,
                        site=site,
                        payload={
                            "recommendation_type": recommendation.recommendation_type,
                            "severity": recommendation.severity,
                            "priority": recommendation.priority,
                            "attention_score": recommendation.attention_score,
                        },
                    )
            for proposal in proposals:
                proposal_policy = PolicyStudioEngine.evaluate(
                    module_slug="ai_agents_center",
                    action_type=proposal.action_type,
                    company=company,
                    site=site,
                    risk_level=getattr(proposal, "priority", "medium"),
                    autonomy_level=agent_definition.autonomy_level,
                    agent_slug=agent_slug,
                    context={"target_entity": proposal.target_entity},
                )
                if not proposal_policy.allowed or proposal_policy.result == PolicyRule.EvaluationResult.DENY:
                    SystemEventService.log_system_event(
                        event_type="policy.overridden",
                        source_module="ai_agents_center",
                        message=proposal_policy.reason,
                        entity_type=proposal.target_entity or proposal.action_type,
                        entity_id=proposal.target_entity_id,
                        user=triggered_by,
                        company=company,
                        site=site,
                        payload={"agent": agent_slug, "action_type": proposal.action_type},
                    )
                    continue
                created_proposal = AgentActionProposal.objects.create(
                    agent_run=run,
                    action_type=proposal.action_type,
                    target_entity=proposal.target_entity,
                    target_entity_id=proposal.target_entity_id,
                    title=proposal.title,
                    summary=proposal.summary,
                    proposed_payload=proposal.proposed_payload,
                    priority=proposal.priority,
                    approval_required=proposal.approval_required,
                )
                created_proposals.append(created_proposal)
                decision_orchestrator = get_decision_orchestrator()
                decision_orchestrator.receive_action_proposal(proposal=created_proposal)
                if agent_definition.domain == agent_definition.Domain.MAINTENANCE:
                    SystemEventService.log_system_event(
                        event_type="agent.maintenance.action.proposed",
                        source_module="ai_agents_center",
                        message="Maintenance action proposal created.",
                        entity_type=proposal.target_entity,
                        entity_id=proposal.target_entity_id,
                        user=triggered_by,
                        company=company,
                        site=site,
                        payload={"action_type": proposal.action_type, "priority": proposal.priority},
                    )
                if agent_definition.domain == agent_definition.Domain.SCHEDULING:
                    SystemEventService.log_system_event(
                        event_type="agent.scheduling.action.proposed",
                        source_module="ai_agents_center",
                        message="Scheduling action proposal created.",
                        entity_type=proposal.target_entity,
                        entity_id=proposal.target_entity_id,
                        user=triggered_by,
                        company=company,
                        site=site,
                        payload={"action_type": proposal.action_type, "priority": proposal.priority},
                    )
                if agent_definition.domain == agent_definition.Domain.PROFITABILITY:
                    SystemEventService.log_system_event(
                        event_type="agent.profitability.action.proposed",
                        source_module="ai_agents_center",
                        message="Profitability action proposal created.",
                        entity_type=proposal.target_entity,
                        entity_id=proposal.target_entity_id,
                        user=triggered_by,
                        company=company,
                        site=site,
                        payload={"action_type": proposal.action_type, "priority": proposal.priority},
                    )
                if agent_definition.domain == agent_definition.Domain.MARKETPLACE:
                    SystemEventService.log_system_event(
                        event_type="agent.marketplace.action.proposed",
                        source_module="ai_agents_center",
                        message="Marketplace action proposal created.",
                        entity_type=proposal.target_entity,
                        entity_id=proposal.target_entity_id,
                        user=triggered_by,
                        company=company,
                        site=site,
                        payload={"action_type": proposal.action_type, "priority": proposal.priority},
                    )
                if agent_definition.domain == agent_definition.Domain.ANOMALY:
                    SystemEventService.log_system_event(
                        event_type="agent.anomaly.action.proposed",
                        source_module="ai_agents_center",
                        message="Anomaly action proposal created.",
                        entity_type=proposal.target_entity,
                        entity_id=proposal.target_entity_id,
                        user=triggered_by,
                        company=company,
                        site=site,
                        payload={"action_type": proposal.action_type, "priority": proposal.priority},
                    )

            attention_map = {}
            for item in created_recommendations:
                attention_map.setdefault(item.entity_id, item)
            asset_lookup = {asset_item["asset_public_id"]: asset_item["asset_id"] for asset_item in context.get("assets", [])}
            for attention_flag in context.get("attention_flags", []):
                recommendation = attention_map.get(attention_flag["asset_public_id"])
                asset_id = asset_lookup.get(attention_flag["asset_public_id"])
                if not asset_id:
                    continue
                AgentAssetAttentionFlag.objects.update_or_create(
                    agent=agent_definition,
                    company=company,
                    asset_id=asset_id,
                    defaults={
                        "site": site,
                        "latest_run": run,
                        "latest_recommendation": recommendation,
                        "status": AgentAssetAttentionFlag.Status.ACTIVE,
                        "attention_score": attention_flag["attention_score"],
                        "summary": attention_flag["summary"],
                        "risk_level": attention_flag["risk_level"],
                        "payload": attention_flag["payload"],
                    },
                )
            schedule_recommendation_map = {}
            for item in created_recommendations:
                schedule_recommendation_map.setdefault(item.entity_id, item)
            for health_flag in context.get("schedule_health_flags", []):
                recommendation = None
                if health_flag.get("technician_id"):
                    recommendation = next(
                        (
                            item
                            for item in created_recommendations
                            if item.payload.get("technician", {}).get("technician_id") == health_flag.get("technician_id")
                        ),
                        None,
                    )
                AgentScheduleHealthFlag.objects.update_or_create(
                    agent=agent_definition,
                    company=company,
                    technician_id=health_flag.get("technician_id"),
                    schedule_date=health_flag.get("schedule_date"),
                    flag_type=health_flag["flag_type"],
                    defaults={
                        "site": site,
                        "latest_run": run,
                        "latest_recommendation": recommendation,
                        "status": AgentScheduleHealthFlag.Status.ACTIVE,
                        "attention_score": health_flag["attention_score"],
                        "summary": health_flag["summary"],
                        "risk_level": health_flag["risk_level"],
                        "payload": health_flag["payload"],
                    },
                )
            for attention_flag in context.get("profitability_flags", []):
                recommendation = next(
                    (
                        item
                        for item in created_recommendations
                        if item.entity_type == attention_flag.get("target_entity_type")
                        and item.entity_id == attention_flag.get("target_entity_id")
                    ),
                    None,
                )
                AgentProfitabilityAttentionFlag.objects.update_or_create(
                    agent=agent_definition,
                    company=company,
                    focus_type=attention_flag["focus_type"],
                    target_entity_type=attention_flag["target_entity_type"],
                    target_entity_id=attention_flag["target_entity_id"],
                    defaults={
                        "site": attention_flag.get("site") or site,
                        "client_id": attention_flag.get("client_id"),
                        "contract_id": attention_flag.get("contract_id"),
                        "technician_id": attention_flag.get("technician_id"),
                        "display_label": attention_flag["display_label"],
                        "latest_run": run,
                        "latest_recommendation": recommendation,
                        "status": AgentProfitabilityAttentionFlag.Status.ACTIVE,
                        "attention_score": attention_flag["attention_score"],
                        "summary": attention_flag["summary"],
                        "risk_level": attention_flag["risk_level"],
                        "payload": attention_flag["payload"],
                    },
                )
            for request_flag in context.get("marketplace_health_flags", []):
                recommendation = next(
                    (
                        item
                        for item in created_recommendations
                        if item.entity_type == "technician_service_request"
                        and item.entity_id == request_flag["service_request_public_id"]
                    ),
                    None,
                )
                AgentMarketplaceRequestFlag.objects.update_or_create(
                    agent=agent_definition,
                    company=company,
                    service_request_id=request_flag["service_request_id"],
                    defaults={
                        "site": request_flag.get("site") or site,
                        "latest_run": run,
                        "latest_recommendation": recommendation,
                        "best_candidate_profile_id": request_flag.get("best_candidate_profile_id"),
                        "status": AgentMarketplaceRequestFlag.Status.ACTIVE,
                        "attention_score": request_flag["attention_score"],
                        "summary": request_flag["summary"],
                        "risk_level": request_flag["risk_level"],
                        "payload": request_flag["payload"],
                    },
                )
            for anomaly_flag in context.get("anomaly_flags", []):
                recommendation = next(
                    (
                        item
                        for item in created_recommendations
                        if item.entity_type == anomaly_flag.get("target_entity_type")
                        and item.entity_id == anomaly_flag.get("target_entity_id")
                    ),
                    None,
                )
                AgentAnomalyAttentionFlag.objects.update_or_create(
                    agent=agent_definition,
                    company=company,
                    focus_type=anomaly_flag["focus_type"],
                    target_entity_type=anomaly_flag["target_entity_type"],
                    target_entity_id=anomaly_flag["target_entity_id"],
                    defaults={
                        "site_id": anomaly_flag.get("site_id") or getattr(site, "id", None),
                        "asset_id": anomaly_flag.get("asset_id"),
                        "client_id": anomaly_flag.get("client_id"),
                        "contract_id": anomaly_flag.get("contract_id"),
                        "technician_id": anomaly_flag.get("technician_id"),
                        "part_id": anomaly_flag.get("part_id"),
                        "display_label": anomaly_flag["display_label"],
                        "latest_run": run,
                        "latest_recommendation": recommendation,
                        "status": AgentAnomalyAttentionFlag.Status.ACTIVE,
                        "attention_score": anomaly_flag["attention_score"],
                        "summary": anomaly_flag["summary"],
                        "risk_level": anomaly_flag["risk_level"],
                        "payload": anomaly_flag["payload"],
                    },
                )

            AgentMemoryService.remember(
                agent=agent_definition,
                company=company,
                site=site,
                entity_type="agent_run",
                entity_id=run.public_id,
                memory_kind="operations_summary",
                content=output_summary,
                metadata={"recommendations": len(created_recommendations), "proposals": len(created_proposals)},
            )

            SystemEventService.log_system_event(
                event_type="agent.run.completed",
                source_module="ai_agents_center",
                message=f"Agent run completed for {agent_slug}.",
                entity_type="agent_run",
                entity_id=str(run.public_id),
                user=triggered_by,
                company=company,
                site=site,
                payload={"recommendations": len(created_recommendations), "proposals": len(created_proposals)},
            )
            if experiment_assignment is not None:
                ExperimentationEngine.record_assignment_metric(
                    assignment=experiment_assignment,
                    metric_type="agent_run_duration_ms",
                    value=run.duration_ms,
                    unit="ms",
                    source_component="ai_agents_center",
                    source_reference=str(run.public_id),
                    metadata={"recommendations": len(created_recommendations), "proposals": len(created_proposals)},
                )
                ExperimentationEngine.record_assignment_metric(
                    assignment=experiment_assignment,
                    metric_type="agent_recommendation_count",
                    value=len(created_recommendations),
                    unit="count",
                    source_component="ai_agents_center",
                    source_reference=str(run.public_id),
                )
                ExperimentationEngine.record_assignment_metric(
                    assignment=experiment_assignment,
                    metric_type="agent_proposal_count",
                    value=len(created_proposals),
                    unit="count",
                    source_component="ai_agents_center",
                    source_reference=str(run.public_id),
                )
            if agent_definition.domain == agent_definition.Domain.MAINTENANCE:
                SystemEventService.log_system_event(
                    event_type="agent.maintenance.run.completed",
                    source_module="ai_agents_center",
                    message="Maintenance intelligence run completed.",
                    entity_type="agent_run",
                    entity_id=str(run.public_id),
                    user=triggered_by,
                    company=company,
                    site=site,
                    payload={
                        "recommendations": len(created_recommendations),
                        "proposals": len(created_proposals),
                        "duration_ms": run.duration_ms,
                    },
                )
            if agent_definition.domain == agent_definition.Domain.SCHEDULING:
                SystemEventService.log_system_event(
                    event_type="agent.scheduling.run.completed",
                    source_module="ai_agents_center",
                    message="Scheduling optimization run completed.",
                    entity_type="agent_run",
                    entity_id=str(run.public_id),
                    user=triggered_by,
                    company=company,
                    site=site,
                    payload={
                        "recommendations": len(created_recommendations),
                        "proposals": len(created_proposals),
                        "duration_ms": run.duration_ms,
                    },
                )
            if agent_definition.domain == agent_definition.Domain.PROFITABILITY:
                SystemEventService.log_system_event(
                    event_type="agent.profitability.run.completed",
                    source_module="ai_agents_center",
                    message="Profitability analysis run completed.",
                    entity_type="agent_run",
                    entity_id=str(run.public_id),
                    user=triggered_by,
                    company=company,
                    site=site,
                    payload={
                        "recommendations": len(created_recommendations),
                        "proposals": len(created_proposals),
                        "duration_ms": run.duration_ms,
                    },
                )
            if agent_definition.domain == agent_definition.Domain.MARKETPLACE:
                SystemEventService.log_system_event(
                    event_type="agent.marketplace.run.completed",
                    source_module="ai_agents_center",
                    message="Marketplace allocation run completed.",
                    entity_type="agent_run",
                    entity_id=str(run.public_id),
                    user=triggered_by,
                    company=company,
                    site=site,
                    payload={
                        "recommendations": len(created_recommendations),
                        "proposals": len(created_proposals),
                        "duration_ms": run.duration_ms,
                    },
                )
            if agent_definition.domain == agent_definition.Domain.ANOMALY:
                SystemEventService.log_system_event(
                    event_type="agent.anomaly.run.completed",
                    source_module="ai_agents_center",
                    message="Anomaly detection run completed.",
                    entity_type="agent_run",
                    entity_id=str(run.public_id),
                    user=triggered_by,
                    company=company,
                    site=site,
                    payload={
                        "recommendations": len(created_recommendations),
                        "proposals": len(created_proposals),
                        "duration_ms": run.duration_ms,
                    },
                )
            JobExecutionTraceService.complete_job(trace=trace, payload={"agent": agent_slug, "status": "completed"})
            return run
        except Exception as exc:
            run.status = AgentRun.Status.FAILED
            run.finished_at = timezone.now()
            run.duration_ms = max(int((run.finished_at - run.started_at).total_seconds() * 1000), 0)
            run.error_message = str(exc)
            run.save(update_fields=["status", "finished_at", "duration_ms", "error_message", "updated_at"])
            assignment_payload = (run.input_context or {}).get("experiment", {})
            if assignment_payload.get("assignment_public_id"):
                assignment = ExperimentationEngine.resolve_assignment(
                    target_component="agent",
                    target_reference=agent_slug,
                    entity_key=f"{getattr(company, 'id', 'global')}:{getattr(site, 'id', 'all')}:{trigger_type}:{trigger_reference or run.public_id}",
                    entity_type="agent_run",
                    company=company,
                    site=site,
                    context={"agent_slug": agent_slug, "trigger_type": trigger_type},
                )
                if assignment is not None:
                    ExperimentationEngine.record_assignment_metric(
                        assignment=assignment,
                        metric_type="agent_run_failure",
                        value=1,
                        unit="count",
                        source_component="ai_agents_center",
                        source_reference=str(run.public_id),
                        metadata={"error": str(exc)},
                    )
            SystemEventService.log_system_event(
                event_type="agent.run.failed",
                source_module="ai_agents_center",
                message=f"Agent run failed for {agent_slug}.",
                severity="error",
                entity_type="agent_run",
                entity_id=str(run.public_id),
                user=triggered_by,
                company=company,
                site=site,
                payload={"error": str(exc)},
            )
            if agent_definition.domain == agent_definition.Domain.MAINTENANCE:
                SystemEventService.log_system_event(
                    event_type="agent.maintenance.run.failed",
                    source_module="ai_agents_center",
                    message="Maintenance intelligence run failed.",
                    severity="error",
                    entity_type="agent_run",
                    entity_id=str(run.public_id),
                    user=triggered_by,
                    company=company,
                    site=site,
                    payload={"error": str(exc)},
                )
            if agent_definition.domain == agent_definition.Domain.SCHEDULING:
                SystemEventService.log_system_event(
                    event_type="agent.scheduling.run.failed",
                    source_module="ai_agents_center",
                    message="Scheduling optimization run failed.",
                    severity="error",
                    entity_type="agent_run",
                    entity_id=str(run.public_id),
                    user=triggered_by,
                    company=company,
                    site=site,
                    payload={"error": str(exc)},
                )
            if agent_definition.domain == agent_definition.Domain.PROFITABILITY:
                SystemEventService.log_system_event(
                    event_type="agent.profitability.run.failed",
                    source_module="ai_agents_center",
                    message="Profitability analysis run failed.",
                    severity="error",
                    entity_type="agent_run",
                    entity_id=str(run.public_id),
                    user=triggered_by,
                    company=company,
                    site=site,
                    payload={"error": str(exc)},
                )
            if agent_definition.domain == agent_definition.Domain.MARKETPLACE:
                SystemEventService.log_system_event(
                    event_type="agent.marketplace.run.failed",
                    source_module="ai_agents_center",
                    message="Marketplace allocation run failed.",
                    severity="error",
                    entity_type="agent_run",
                    entity_id=str(run.public_id),
                    user=triggered_by,
                    company=company,
                    site=site,
                    payload={"error": str(exc)},
                )
            if agent_definition.domain == agent_definition.Domain.ANOMALY:
                SystemEventService.log_system_event(
                    event_type="agent.anomaly.run.failed",
                    source_module="ai_agents_center",
                    message="Anomaly detection run failed.",
                    severity="error",
                    entity_type="agent_run",
                    entity_id=str(run.public_id),
                    user=triggered_by,
                    company=company,
                    site=site,
                    payload={"error": str(exc)},
                )
            JobExecutionTraceService.fail_job(trace=trace, error_message=str(exc), payload={"agent": agent_slug})
            raise

    @classmethod
    def approve_proposal(cls, *, proposal, approved_by, company=None):
        decision = getattr(proposal, "decision", None)
        if decision is None:
            decision_orchestrator = get_decision_orchestrator()
            decision = decision_orchestrator.receive_action_proposal(proposal=proposal)
        decision_orchestrator = get_decision_orchestrator()
        decision_orchestrator.approve_decision(decision=decision, approved_by=approved_by, comment="")
        proposal.refresh_from_db()
        return proposal

    @classmethod
    def reject_proposal(cls, *, proposal, rejected_by, company=None, reason=""):
        decision = getattr(proposal, "decision", None)
        if decision is None:
            decision_orchestrator = get_decision_orchestrator()
            decision = decision_orchestrator.receive_action_proposal(proposal=proposal)
        decision_orchestrator = get_decision_orchestrator()
        decision_orchestrator.reject_decision(decision=decision, rejected_by=rejected_by, comment=reason)
        proposal.refresh_from_db()
        return proposal
