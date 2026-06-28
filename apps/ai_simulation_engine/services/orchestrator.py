from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.ai_decision_engine.models import AgentDecision
from apps.ai_experimentation_framework.services.engine import ExperimentationEngine
from apps.ai_optimization_loop.services.orchestrator import LearningOrchestrator
from apps.ai_policy_studio.models import PolicyRule
from apps.ai_policy_studio.services.engine import PolicyStudioEngine
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import Asset
from shared_kernel.observability.context import get_request_id

from ..models import SimulationResult, SimulationRun, SimulationScenario, SimulationType
from .audit import SimulationAuditService
from .handlers import SimulationHandlerRegistry
from .policies import SimulationPolicyService


class SimulationOrchestrator:
    @classmethod
    def resolve_type_for_decision(cls, decision: AgentDecision):
        requirement = SimulationPolicyService.get_requirement_for_decision(decision)
        if requirement is None:
            return None
        return SimulationType.objects.filter(slug=requirement["simulation_type"], enabled=True).first()

    @classmethod
    def build_input_for_decision(cls, decision: AgentDecision, simulation_type: str):
        payload = dict(decision.agent_action_proposal.proposed_payload or {})
        payload.setdefault("date", timezone.localdate().isoformat())
        if simulation_type == "route_reorder_simulation":
            payload.setdefault("technician_id", payload.get("technician_id"))
        if simulation_type == "technician_reassignment_simulation":
            if decision.target_entity == "scheduled_visit":
                payload.setdefault("visit_public_id", payload.get("visit_public_id") or decision.target_entity_id)
            payload.setdefault("to_technician_id", payload.get("to_technician_id") or payload.get("technician_id"))
        if simulation_type == "preventive_frequency_change_simulation":
            asset_public_id = payload.get("asset_public_id")
            if not asset_public_id and decision.target_entity == "asset":
                asset_public_id = decision.target_entity_id
            if not asset_public_id and decision.site is not None:
                asset_public_id = (
                    Asset.objects.filter(operational_site=decision.site)
                    .order_by("id")
                    .values_list("public_id", flat=True)
                    .first()
                )
            if not asset_public_id:
                run_context = getattr(decision.agent_action_proposal.agent_run, "input_context", {}) or {}
                candidate_assets = payload.get("asset_analysis") or run_context.get("asset_analysis") or []
                asset_public_id = next((row.get("asset_public_id") for row in candidate_assets if row.get("asset_public_id")), None)
            if asset_public_id:
                payload["asset_public_id"] = asset_public_id
            payload.setdefault("proposed_frequency_days", 15)
        if simulation_type == "contract_repricing_simulation":
            contract_public_id = payload.get("contract_public_id")
            if not contract_public_id and decision.target_entity == "maintenance_contract":
                contract_public_id = decision.target_entity_id
            if not contract_public_id and decision.target_entity == "maintenance_client":
                run_context = getattr(decision.agent_action_proposal.agent_run, "input_context", {}) or {}
                candidate_rows = payload.get("contract_rows") or run_context.get("contract_rows") or []
                contract_public_id = next((row.get("contract_public_id") for row in candidate_rows if row.get("contract_public_id")), None)
            if contract_public_id:
                payload["contract_public_id"] = contract_public_id
        if simulation_type == "marketplace_candidate_swap_simulation":
            payload.setdefault("service_request_public_id", payload.get("service_request_public_id") or decision.target_entity_id)
            if payload.get("marketplace_candidates") and not payload.get("proposed_candidate_public_id"):
                payload["proposed_candidate_public_id"] = payload["marketplace_candidates"][0].get("technician_profile_public_id")
        if simulation_type == "maintenance_action_plan_simulation":
            asset_public_id = payload.get("asset_public_id")
            if not asset_public_id and decision.target_entity == "asset":
                asset_public_id = decision.target_entity_id
            if not asset_public_id and decision.site is not None:
                asset_public_id = (
                    Asset.objects.filter(operational_site=decision.site)
                    .order_by("id")
                    .values_list("public_id", flat=True)
                    .first()
                )
            if asset_public_id:
                payload.setdefault("asset_public_id", str(asset_public_id))
        return payload

    @classmethod
    @transaction.atomic
    def simulate_for_decision(cls, *, decision: AgentDecision, requested_by=None, force=False):
        simulation_type = cls.resolve_type_for_decision(decision)
        if simulation_type is None:
            return None
        studio_result = PolicyStudioEngine.evaluate(
            module_slug="ai_simulation_engine",
            action_type=simulation_type.slug,
            company=decision.company,
            site=decision.site,
            risk_level=decision.risk_level,
            autonomy_level=decision.autonomy_level,
            agent_slug=decision.agent_action_proposal.agent_run.agent.slug,
            context={"decision_public_id": str(decision.public_id)},
        )
        if not studio_result.allowed or studio_result.result == PolicyRule.EvaluationResult.DENY:
            raise PermissionError(studio_result.reason)
        if not force:
            latest = decision.simulation_runs.select_related("result", "scenario", "scenario__simulation_type").order_by("-created_at").first()
            if latest and latest.status == SimulationRun.RunStatus.COMPLETED:
                return latest
        input_payload = cls.build_input_for_decision(decision, simulation_type.slug)
        if simulation_type.slug == "technician_reassignment_simulation" and (
            not input_payload.get("visit_public_id") or not input_payload.get("to_technician_id")
        ):
            return None
        scenario, _ = SimulationScenario.objects.get_or_create(
            simulation_type=simulation_type,
            company=decision.company,
            site=decision.site,
            target_entity=decision.target_entity,
            target_entity_id=decision.target_entity_id,
            title=f"{simulation_type.name} for {decision.normalized_action_type}",
            defaults={
                "description": decision.agent_action_proposal.summary,
                "status": SimulationScenario.ScenarioStatus.READY,
                "created_by_user": requested_by or decision.agent_action_proposal.agent_run.triggered_by,
            },
        )
        simulation_run = SimulationRun.objects.create(
            scenario=scenario,
            decision=decision,
            trigger_type=SimulationRun.TriggerType.DECISION,
            source_type=SimulationRun.SourceType.DECISION,
            source_reference=str(decision.public_id),
            input_payload=input_payload,
            status=SimulationRun.RunStatus.PENDING,
            request_id=get_request_id(),
            created_by_user=requested_by or decision.agent_action_proposal.agent_run.triggered_by,
        )
        SystemEventService.log_system_event(
            event_type="simulation.requested",
            source_module="ai_simulation_engine",
            message="Simulation requested.",
            entity_type=decision.target_entity or simulation_type.slug,
            entity_id=decision.target_entity_id or str(simulation_run.public_id),
            user=requested_by,
            company=decision.company,
            site=decision.site,
            payload={"simulation_type": simulation_type.slug, "decision_public_id": str(decision.public_id)},
        )
        SimulationAuditService.log_event(
            simulation_run=simulation_run,
            event_type="simulation.requested",
            actor_user=requested_by,
            message="Simulation requested by orchestrator.",
            payload={"simulation_type": simulation_type.slug},
        )
        return cls.run(simulation_run=simulation_run)

    @classmethod
    @transaction.atomic
    def run(cls, *, simulation_run: SimulationRun):
        handler = SimulationHandlerRegistry.get_handler(simulation_run.scenario.simulation_type.slug)
        if handler is None:
            raise ValueError(f"No simulation handler for {simulation_run.scenario.simulation_type.slug}.")
        experiment_assignment = ExperimentationEngine.resolve_assignment(
            target_component="simulation_engine",
            target_reference=simulation_run.scenario.simulation_type.slug,
            entity_key=str(simulation_run.public_id),
            entity_type="simulation_run",
            company=simulation_run.scenario.company,
            site=simulation_run.scenario.site,
            context={"trigger_type": simulation_run.trigger_type, "source_type": simulation_run.source_type},
        )
        simulation_run.status = SimulationRun.RunStatus.RUNNING
        simulation_run.started_at = timezone.now()
        simulation_run.save(update_fields=["status", "started_at", "updated_at"])
        scenario = simulation_run.scenario
        scenario.status = SimulationScenario.ScenarioStatus.RUNNING
        scenario.save(update_fields=["status", "updated_at"])
        SystemEventService.log_system_event(
            event_type="simulation.run.started",
            source_module="ai_simulation_engine",
            message="Simulation run started.",
            entity_type=scenario.target_entity or scenario.simulation_type.slug,
            entity_id=scenario.target_entity_id or str(simulation_run.public_id),
            user=simulation_run.created_by_user,
            company=scenario.company,
            site=scenario.site,
            payload={"simulation_type": scenario.simulation_type.slug},
        )
        try:
            computation = handler.run(
                company=scenario.company,
                site=scenario.site,
                input_payload=simulation_run.input_payload,
            )
            simulation_run.baseline_snapshot = computation.baseline_snapshot
            simulation_run.status = SimulationRun.RunStatus.COMPLETED
            simulation_run.finished_at = timezone.now()
            simulation_run.save(update_fields=["baseline_snapshot", "status", "finished_at", "updated_at"])
            SimulationResult.objects.update_or_create(
                simulation_run=simulation_run,
                defaults={
                    "summary": computation.summary,
                    "impact_score": computation.impact_score,
                    "confidence_level": computation.confidence_level,
                    "risk_delta": computation.risk_delta,
                    "cost_delta": computation.cost_delta,
                    "sla_delta": computation.sla_delta,
                    "profit_delta": computation.profit_delta,
                    "travel_delta": computation.travel_delta,
                    "workload_delta": computation.workload_delta,
                    "recommendation": computation.recommendation,
                    "result_payload": computation.result_payload,
                },
            )
            scenario.status = SimulationScenario.ScenarioStatus.COMPLETED
            scenario.save(update_fields=["status", "updated_at"])
            SimulationAuditService.log_event(
                simulation_run=simulation_run,
                event_type="simulation.run.completed",
                actor_user=simulation_run.created_by_user,
                message=computation.summary,
                payload={"confidence_level": computation.confidence_level},
            )
            SystemEventService.log_system_event(
                event_type="simulation.run.completed",
                source_module="ai_simulation_engine",
                message=computation.summary,
                entity_type=scenario.target_entity or scenario.simulation_type.slug,
                entity_id=scenario.target_entity_id or str(simulation_run.public_id),
                user=simulation_run.created_by_user,
                company=scenario.company,
                site=scenario.site,
                payload={
                    "simulation_type": scenario.simulation_type.slug,
                    "confidence_level": computation.confidence_level,
                    "duration_ms": max(int((simulation_run.finished_at - simulation_run.started_at).total_seconds() * 1000), 0),
                },
            )
            if simulation_run.decision_id:
                decision = simulation_run.decision
                decision.explainability_payload = {
                    **(decision.explainability_payload or {}),
                    "simulation": {
                        "simulation_run_public_id": str(simulation_run.public_id),
                        "simulation_type": scenario.simulation_type.slug,
                        "summary": computation.summary,
                        "confidence_level": computation.confidence_level,
                    },
                }
                decision.save(update_fields=["explainability_payload", "updated_at"])
                SystemEventService.log_system_event(
                    event_type="simulation.result.attached_to_decision",
                    source_module="ai_simulation_engine",
                    message="Simulation result attached to decision.",
                    entity_type=decision.target_entity or decision.normalized_action_type,
                    entity_id=decision.target_entity_id or str(decision.public_id),
                    company=decision.company,
                    site=decision.site,
                    payload={"decision_public_id": str(decision.public_id), "simulation_run_public_id": str(simulation_run.public_id)},
                )
            if experiment_assignment is not None:
                ExperimentationEngine.record_assignment_metric(
                    assignment=experiment_assignment,
                    metric_type="simulation_impact_score",
                    value=computation.impact_score,
                    unit="score",
                    source_component="ai_simulation_engine",
                    source_reference=str(simulation_run.public_id),
                    metadata={"confidence_level": computation.confidence_level},
                )
                ExperimentationEngine.record_assignment_metric(
                    assignment=experiment_assignment,
                    metric_type="simulation_duration_ms",
                    value=max(int((simulation_run.finished_at - simulation_run.started_at).total_seconds() * 1000), 0),
                    unit="ms",
                    source_component="ai_simulation_engine",
                    source_reference=str(simulation_run.public_id),
                )
            LearningOrchestrator.measure_simulation(simulation_run=simulation_run)
            return simulation_run
        except Exception as exc:
            simulation_run.status = SimulationRun.RunStatus.FAILED
            simulation_run.finished_at = timezone.now()
            simulation_run.save(update_fields=["status", "finished_at", "updated_at"])
            scenario.status = SimulationScenario.ScenarioStatus.FAILED
            scenario.save(update_fields=["status", "updated_at"])
            SimulationAuditService.log_event(
                simulation_run=simulation_run,
                event_type="simulation.run.failed",
                actor_user=simulation_run.created_by_user,
                message=str(exc),
            )
            SystemEventService.log_system_event(
                event_type="simulation.run.failed",
                source_module="ai_simulation_engine",
                message="Simulation run failed.",
                severity="error",
                entity_type=scenario.target_entity or scenario.simulation_type.slug,
                entity_id=scenario.target_entity_id or str(simulation_run.public_id),
                user=simulation_run.created_by_user,
                company=scenario.company,
                site=scenario.site,
                payload={"simulation_type": scenario.simulation_type.slug, "error": str(exc)},
            )
            if experiment_assignment is not None:
                ExperimentationEngine.record_assignment_metric(
                    assignment=experiment_assignment,
                    metric_type="simulation_failure",
                    value=1,
                    unit="count",
                    source_component="ai_simulation_engine",
                    source_reference=str(simulation_run.public_id),
                    metadata={"error": str(exc)},
                )
            raise
