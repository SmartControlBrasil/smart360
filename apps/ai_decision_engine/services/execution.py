from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.ai_decision_engine.models import AgentDecision, DecisionExecution
from apps.ai_experimentation_framework.models import ExperimentAssignment
from apps.ai_experimentation_framework.services.engine import ExperimentationEngine
from apps.ai_optimization_loop.services.orchestrator import LearningOrchestrator
from apps.observability_center.services.observability_service import SystemEventService

from .audit import DecisionAuditService
from .handlers import DecisionHandlerRegistry


class DecisionExecutionService:
    @staticmethod
    def _experiment_assignment_for(decision: AgentDecision):
        payload = (decision.explainability_payload or {}).get("experiment", {})
        assignment_public_id = payload.get("assignment_public_id")
        if not assignment_public_id:
            return None
        return ExperimentAssignment.objects.select_related("experiment", "variant").filter(public_id=assignment_public_id).first()

    @classmethod
    @transaction.atomic
    def execute(cls, *, decision: AgentDecision, executed_by_mode: str, executed_by_user=None):
        handler = DecisionHandlerRegistry.get_handler(decision.normalized_action_type)
        if handler is None:
            raise ValueError(f"No handler registered for {decision.normalized_action_type}.")
        started_at = timezone.now()
        execution = DecisionExecution.objects.create(
            decision=decision,
            execution_status=DecisionExecution.ExecutionStatus.RUNNING,
            executed_by_mode=executed_by_mode,
            executed_by_user=executed_by_user,
            executed_at=started_at,
            rollback_supported=decision.rollback_required,
            rollback_status=DecisionExecution.RollbackStatus.AVAILABLE if decision.rollback_required else DecisionExecution.RollbackStatus.NOT_REQUIRED,
        )
        SystemEventService.log_system_event(
            event_type="decision.execution.started",
            source_module="ai_decision_engine",
            message="Decision execution started.",
            entity_type=decision.target_entity or decision.normalized_action_type,
            entity_id=decision.target_entity_id or str(decision.public_id),
            user=executed_by_user,
            company=decision.company,
            site=decision.site,
            payload={"decision_public_id": str(decision.public_id), "action_type": decision.normalized_action_type},
        )
        DecisionAuditService.log_event(
            decision=decision,
            event_type="decision.execution.started",
            actor_mode="handler",
            actor_user=executed_by_user,
            actor_label=handler.__class__.__name__,
            message=f"Execucao iniciada por {handler.__class__.__name__}.",
        )
        try:
            result = handler.execute(decision=decision, actor=executed_by_user)
            finished_at = timezone.now()
            execution.execution_status = DecisionExecution.ExecutionStatus.SUCCEEDED
            execution.execution_summary = result.summary
            execution.result_payload = result.payload
            execution.finished_at = finished_at
            execution.duration_ms = max(int((finished_at - started_at).total_seconds() * 1000), 0)
            execution.rollback_supported = result.rollback_supported
            execution.rollback_status = (
                DecisionExecution.RollbackStatus.AVAILABLE if result.rollback_supported else DecisionExecution.RollbackStatus.NOT_REQUIRED
            )
            execution.save(
                update_fields=[
                    "execution_status",
                    "execution_summary",
                    "result_payload",
                    "finished_at",
                    "duration_ms",
                    "rollback_supported",
                    "rollback_status",
                    "updated_at",
                ]
            )
            decision.decision_status = AgentDecision.DecisionStatus.EXECUTED
            decision.decision_reason = result.summary
            decision.decided_by_user = executed_by_user or decision.decided_by_user
            decision.decided_at = finished_at
            decision.execution_payload = {
                **(decision.execution_payload or {}),
                "last_execution": result.payload,
                "related_entity_type": result.related_entity_type,
                "related_entity_id": result.related_entity_id,
            }
            decision.save(update_fields=["decision_status", "decision_reason", "decided_by_user", "decided_at", "execution_payload", "updated_at"])
            DecisionAuditService.log_event(
                decision=decision,
                event_type="decision.execution.succeeded",
                actor_mode="handler",
                actor_user=executed_by_user,
                actor_label=handler.__class__.__name__,
                message=result.summary,
                metadata=result.payload,
            )
            SystemEventService.log_system_event(
                event_type="decision.execution.succeeded",
                source_module="ai_decision_engine",
                message=result.summary,
                entity_type=result.related_entity_type,
                entity_id=result.related_entity_id,
                user=executed_by_user,
                company=decision.company,
                site=decision.site,
                payload={
                    "decision_public_id": str(decision.public_id),
                    "action_type": decision.normalized_action_type,
                    "duration_ms": execution.duration_ms,
                    **result.payload,
                },
            )
            assignment = cls._experiment_assignment_for(decision)
            if assignment is not None:
                ExperimentationEngine.record_assignment_metric(
                    assignment=assignment,
                    metric_type="decision_execution_success",
                    value=1,
                    unit="count",
                    source_component="ai_decision_engine",
                    source_reference=str(decision.public_id),
                    metadata={"duration_ms": execution.duration_ms},
                )
                ExperimentationEngine.record_assignment_metric(
                    assignment=assignment,
                    metric_type="decision_execution_duration_ms",
                    value=execution.duration_ms,
                    unit="ms",
                    source_component="ai_decision_engine",
                    source_reference=str(decision.public_id),
                )
            LearningOrchestrator.measure_decision(decision=decision, execution=execution)
            return execution
        except Exception as exc:
            finished_at = timezone.now()
            execution.execution_status = DecisionExecution.ExecutionStatus.FAILED
            execution.error_message = str(exc)
            execution.finished_at = finished_at
            execution.duration_ms = max(int((finished_at - started_at).total_seconds() * 1000), 0)
            execution.save(update_fields=["execution_status", "error_message", "finished_at", "duration_ms", "updated_at"])
            decision.decision_status = AgentDecision.DecisionStatus.FAILED
            decision.decision_reason = str(exc)
            decision.decided_by_user = executed_by_user or decision.decided_by_user
            decision.decided_at = finished_at
            decision.save(update_fields=["decision_status", "decision_reason", "decided_by_user", "decided_at", "updated_at"])
            DecisionAuditService.log_event(
                decision=decision,
                event_type="decision.execution.failed",
                actor_mode="handler",
                actor_user=executed_by_user,
                actor_label=handler.__class__.__name__,
                message=f"Execucao falhou: {exc}",
            )
            SystemEventService.log_system_event(
                event_type="decision.execution.failed",
                source_module="ai_decision_engine",
                message="Decision execution failed.",
                severity="error",
                entity_type=decision.target_entity or decision.normalized_action_type,
                entity_id=decision.target_entity_id or str(decision.public_id),
                user=executed_by_user,
                company=decision.company,
                site=decision.site,
                payload={
                    "decision_public_id": str(decision.public_id),
                    "action_type": decision.normalized_action_type,
                    "error": str(exc),
                    "duration_ms": execution.duration_ms,
                },
            )
            assignment = cls._experiment_assignment_for(decision)
            if assignment is not None:
                ExperimentationEngine.record_assignment_metric(
                    assignment=assignment,
                    metric_type="decision_execution_failure",
                    value=1,
                    unit="count",
                    source_component="ai_decision_engine",
                    source_reference=str(decision.public_id),
                    metadata={"error": str(exc), "duration_ms": execution.duration_ms},
                )
            LearningOrchestrator.measure_decision(decision=decision, execution=execution)
            raise
