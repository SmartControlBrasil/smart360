from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.ai_autonomous_ops.models import AutonomousExecution
from apps.ai_shared.interfaces.decision_engine import get_decision_execution_service
from apps.ai_decision_engine.models import AgentDecision, DecisionExecution
from apps.ai_simulation_engine.models import SimulationType
from apps.ai_simulation_engine.services.orchestrator import SimulationOrchestrator
from apps.ai_simulation_engine.services.policies import SimulationPolicyService
from apps.ai_policy_studio.models import PolicyRule
from apps.ai_policy_studio.services.engine import PolicyStudioEngine

from .audit import AutonomousAuditService
from .guards import AutonomousGuardService
from .policies import AutonomousPolicyService
from .rollback import AutonomousRollbackService


class AutonomousOperationsService:
    @classmethod
    @transaction.atomic
    def evaluate_and_execute(cls, *, decision: AgentDecision):
        simulation_run = None
        envelope = AutonomousPolicyService.evaluate_safety_envelope(decision=decision, simulation_run=None)
        required_simulation = SimulationPolicyService.get_requirement_for_decision(decision)
        if envelope.requires_simulation and required_simulation is not None:
            simulation_type = SimulationType.objects.filter(slug=required_simulation["simulation_type"], enabled=True).first()
            if simulation_type is None:
                execution = AutonomousExecution.objects.create(
                    company=decision.company,
                    site=decision.site,
                    action_type=decision.normalized_action_type,
                    source_agent=decision.agent_action_proposal.agent_run.agent.slug,
                    source_decision=decision,
                    risk_level=decision.risk_level,
                    execution_status=AutonomousExecution.ExecutionStatus.BLOCKED,
                    execution_summary="Simulacao obrigatoria ausente.",
                    policy_snapshot={
                        **envelope.policy_payload,
                        "policy_studio_result": "",
                        "policy_studio_reason": "",
                        "required_simulation_type": required_simulation["simulation_type"],
                    },
                )
                AutonomousAuditService.log_event(
                    execution=execution,
                    event_type="autonomy.simulation.failed",
                    message="Simulacao obrigatoria ausente.",
                )
                decision.explainability_payload = {
                    **(decision.explainability_payload or {}),
                    "autonomy": {
                        "candidate": True,
                        "autonomous_execution_public_id": str(execution.public_id),
                        "safety_envelope": execution.policy_snapshot,
                    },
                }
                decision.save(update_fields=["explainability_payload", "updated_at"])
                return execution
        studio_result = PolicyStudioEngine.evaluate(
            module_slug="ai_autonomous_ops",
            action_type="evaluate_candidate",
            company=decision.company,
            site=decision.site,
            risk_level=decision.risk_level,
            autonomy_level=decision.autonomy_level,
            agent_slug=decision.agent_action_proposal.agent_run.agent.slug,
            context={"action_type": decision.normalized_action_type},
        )
        execution = AutonomousExecution.objects.create(
            company=decision.company,
            site=decision.site,
            action_type=decision.normalized_action_type,
            source_agent=decision.agent_action_proposal.agent_run.agent.slug,
            source_decision=decision,
            risk_level=decision.risk_level,
            execution_status=AutonomousExecution.ExecutionStatus.CANDIDATE,
            policy_snapshot=envelope.policy_payload,
        )
        AutonomousAuditService.log_event(
            execution=execution,
            event_type="autonomy.candidate.received",
            message="Candidato de autonomia recebido do Decision Engine.",
            payload={"decision_public_id": str(decision.public_id)},
        )
        execution.policy_snapshot = {
            **execution.policy_snapshot,
            "policy_studio_result": studio_result.result,
            "policy_studio_reason": studio_result.reason,
        }
        execution.save(update_fields=["policy_snapshot", "updated_at"])
        decision.explainability_payload = {
            **(decision.explainability_payload or {}),
            "autonomy": {
                "candidate": True,
                "autonomous_execution_public_id": str(execution.public_id),
                "safety_envelope": execution.policy_snapshot,
            },
        }
        decision.save(update_fields=["explainability_payload", "updated_at"])
        if studio_result.policy is not None and studio_result.result == PolicyRule.EvaluationResult.DENY:
            execution.execution_status = AutonomousExecution.ExecutionStatus.BLOCKED
            execution.execution_summary = studio_result.reason
            execution.save(update_fields=["execution_status", "execution_summary", "updated_at"])
            AutonomousAuditService.log_event(execution=execution, event_type="autonomy.policy.blocked", message=studio_result.reason)
            return execution
        if not envelope.allowed:
            execution.execution_status = AutonomousExecution.ExecutionStatus.BLOCKED
            execution.execution_summary = envelope.reason
            execution.save(update_fields=["execution_status", "execution_summary", "updated_at"])
            AutonomousAuditService.log_event(execution=execution, event_type="autonomy.policy.blocked", message=envelope.reason)
            return execution
        AutonomousAuditService.log_event(execution=execution, event_type="autonomy.policy.allowed", message=envelope.reason)
        if envelope.requires_simulation:
            AutonomousAuditService.log_event(execution=execution, event_type="autonomy.simulation.required", message="Simulacao previa obrigatoria.")
            simulation_run = SimulationOrchestrator.simulate_for_decision(
                decision=decision,
                requested_by=decision.agent_action_proposal.agent_run.triggered_by,
                force=False,
            )
            execution.source_simulation = simulation_run
            execution.save(update_fields=["source_simulation", "updated_at"])
            if simulation_run is None or not hasattr(simulation_run, "result"):
                execution.execution_status = AutonomousExecution.ExecutionStatus.BLOCKED
                execution.execution_summary = "Simulacao obrigatoria ausente."
                execution.save(update_fields=["execution_status", "execution_summary", "updated_at"])
                AutonomousAuditService.log_event(execution=execution, event_type="autonomy.simulation.failed", message="Simulacao obrigatoria ausente.")
                return execution
            AutonomousAuditService.log_event(
                execution=execution,
                event_type="autonomy.simulation.passed",
                message="Simulacao previa concluida com resultado utilizavel.",
                payload={"simulation_run_public_id": str(simulation_run.public_id), "confidence_level": simulation_run.result.confidence_level},
            )
        confidence_score = AutonomousPolicyService.compute_confidence_score(decision=decision, simulation_run=simulation_run)
        execution.confidence_score = confidence_score
        execution.confidence_level = getattr(getattr(simulation_run, "result", None), "confidence_level", "medium" if confidence_score >= 0.78 else "low")
        execution.policy_snapshot = {**execution.policy_snapshot, "threshold": str(envelope.threshold)}
        execution.save(update_fields=["confidence_score", "confidence_level", "policy_snapshot", "updated_at"])
        if confidence_score < envelope.threshold:
            execution.execution_status = AutonomousExecution.ExecutionStatus.BLOCKED
            execution.execution_summary = "Confidence score abaixo do threshold configurado."
            execution.save(update_fields=["execution_status", "execution_summary", "updated_at"])
            AutonomousAuditService.log_event(execution=execution, event_type="autonomy.policy.blocked", message=execution.execution_summary)
            return execution
        guard_result = AutonomousGuardService.evaluate(config=envelope.config, decision=decision, confidence_score=confidence_score)
        execution.guard_snapshot = guard_result.payload
        execution.save(update_fields=["guard_snapshot", "updated_at"])
        if not guard_result.allowed:
            execution.execution_status = AutonomousExecution.ExecutionStatus.BLOCKED
            execution.execution_summary = guard_result.reason
            execution.save(update_fields=["execution_status", "execution_summary", "updated_at"])
            AutonomousAuditService.log_event(execution=execution, event_type="autonomy.policy.blocked", message=guard_result.reason)
            return execution
        execution.execution_status = AutonomousExecution.ExecutionStatus.RUNNING
        execution.started_at = timezone.now()
        execution.save(update_fields=["execution_status", "started_at", "updated_at"])
        AutonomousAuditService.log_event(execution=execution, event_type="autonomy.execution.started", message="Autoexecucao iniciada.")
        execute_result = PolicyStudioEngine.evaluate(
            module_slug="ai_autonomous_ops",
            action_type="execute_autonomy",
            company=decision.company,
            site=decision.site,
            risk_level=decision.risk_level,
            autonomy_level=decision.autonomy_level,
            agent_slug=decision.agent_action_proposal.agent_run.agent.slug,
            context={"action_type": decision.normalized_action_type},
        )
        if not execute_result.allowed:
            execution.execution_status = AutonomousExecution.ExecutionStatus.BLOCKED
            execution.execution_summary = execute_result.reason
            execution.save(update_fields=["execution_status", "execution_summary", "updated_at"])
            AutonomousAuditService.log_event(execution=execution, event_type="autonomy.policy.blocked", message=execute_result.reason)
            return execution
        try:
            decision_execution_service = get_decision_execution_service()
            decision_execution = decision_execution_service.execute(
                decision=decision,
                executed_by_mode=DecisionExecution.ExecutedByMode.AUTO,
                executed_by_user=None,
            )
            execution.execution_status = AutonomousExecution.ExecutionStatus.SUCCEEDED
            execution.execution_summary = decision_execution.execution_summary
            execution.rollback_supported = decision_execution.rollback_supported
            execution.rollback_status = (
                AutonomousExecution.RollbackStatus.AVAILABLE if decision_execution.rollback_supported else AutonomousExecution.RollbackStatus.NOT_REQUIRED
            )
            execution.expected_outcome = {
                "decision_reason": decision.decision_reason,
                "simulation_summary": getattr(getattr(simulation_run, "result", None), "summary", ""),
                "simulation_confidence": getattr(getattr(simulation_run, "result", None), "confidence_level", ""),
            }
            execution.result_payload = decision_execution.result_payload
            execution.finished_at = timezone.now()
            execution.save(
                update_fields=[
                    "execution_status",
                    "execution_summary",
                    "rollback_supported",
                    "rollback_status",
                    "expected_outcome",
                    "result_payload",
                    "finished_at",
                    "updated_at",
                ]
            )
            AutonomousAuditService.log_event(execution=execution, event_type="autonomy.execution.succeeded", message=execution.execution_summary)
            decision.explainability_payload = {
                **(decision.explainability_payload or {}),
                "autonomy": {
                    "candidate": True,
                    "autonomous_execution_public_id": str(execution.public_id),
                    "status": execution.execution_status,
                    "confidence_score": str(execution.confidence_score),
                    "confidence_level": execution.confidence_level,
                    "simulation_run_public_id": str(simulation_run.public_id) if simulation_run else "",
                    "rollback_supported": execution.rollback_supported,
                },
            }
            decision.save(update_fields=["explainability_payload", "updated_at"])
            return execution
        except Exception as exc:
            execution.execution_status = AutonomousExecution.ExecutionStatus.FAILED
            execution.execution_summary = str(exc)
            execution.finished_at = timezone.now()
            execution.save(update_fields=["execution_status", "execution_summary", "finished_at", "updated_at"])
            AutonomousAuditService.log_event(execution=execution, event_type="autonomy.execution.failed", message=str(exc))
            AutonomousAuditService.create_incident(
                execution=execution,
                incident_type="execution_failed",
                summary="Autoexecucao falhou e gerou incidente.",
                severity="high",
                payload={"error": str(exc)},
            )
            raise

    @classmethod
    def rollback(cls, *, autonomous_execution: AutonomousExecution, requested_by=None):
        return AutonomousRollbackService.rollback(autonomous_execution=autonomous_execution, requested_by=requested_by)
