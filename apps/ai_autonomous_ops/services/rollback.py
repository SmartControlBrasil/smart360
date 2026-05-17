from apps.ai_agents_center.models import AgentAssetAttentionFlag, AgentProfitabilityAttentionFlag
from apps.ai_autonomous_ops.models import AutonomousExecution
from apps.ai_policy_studio.models import PolicyRule
from apps.ai_policy_studio.services.engine import PolicyStudioEngine
from apps.smart_system.models import RoutePlan

from .audit import AutonomousAuditService


class AutonomousRollbackService:
    @classmethod
    def rollback(cls, *, autonomous_execution: AutonomousExecution, requested_by=None):
        payload = autonomous_execution.result_payload or {}
        action_type = autonomous_execution.action_type
        source_decision = autonomous_execution.source_decision
        studio_result = PolicyStudioEngine.evaluate(
            module_slug="ai_autonomous_ops",
            action_type="rollback_autonomy",
            company=autonomous_execution.company,
            site=autonomous_execution.site,
            risk_level=autonomous_execution.risk_level,
            autonomy_level=getattr(source_decision, "autonomy_level", 0),
            agent_slug=autonomous_execution.source_agent,
            context={"action_type": action_type, "execution_public_id": str(autonomous_execution.public_id)},
        )
        if not studio_result.allowed or studio_result.result == PolicyRule.EvaluationResult.DENY:
            AutonomousAuditService.log_event(
                execution=autonomous_execution,
                event_type="autonomy.rollback.failed",
                message=studio_result.reason,
                actor_user=requested_by,
            )
            AutonomousAuditService.create_incident(
                execution=autonomous_execution,
                incident_type="rollback_denied",
                summary="Rollback bloqueado por policy studio.",
                severity="medium",
                payload={"reason": studio_result.reason},
            )
            raise PermissionError(studio_result.reason)
        AutonomousAuditService.log_event(
            execution=autonomous_execution,
            event_type="autonomy.rollback.started",
            message="Rollback de autonomia iniciado.",
            actor_user=requested_by,
        )
        if action_type == "mark_asset_attention" and payload.get("flag_public_id"):
            flag = AgentAssetAttentionFlag.objects.get(public_id=payload["flag_public_id"])
            flag.status = AgentAssetAttentionFlag.Status.RESOLVED
            flag.save(update_fields=["status", "updated_at"])
        elif action_type == "flag_contract_profitability_attention" and payload.get("flag_public_id"):
            flag = AgentProfitabilityAttentionFlag.objects.get(public_id=payload["flag_public_id"])
            flag.status = AgentProfitabilityAttentionFlag.Status.RESOLVED
            flag.save(update_fields=["status", "updated_at"])
        elif action_type == "reorder_route_proposal" and payload.get("route_plan_public_id"):
            route_plan = RoutePlan.objects.get(public_id=payload["route_plan_public_id"])
            route_plan.optimization_status = RoutePlan.OptimizationStatus.NEEDS_REVIEW
            route_plan.route_summary = {}
            route_plan.save(update_fields=["optimization_status", "route_summary", "updated_at"])
        else:
            autonomous_execution.rollback_status = AutonomousExecution.RollbackStatus.FAILED
            autonomous_execution.save(update_fields=["rollback_status", "updated_at"])
            AutonomousAuditService.log_event(
                execution=autonomous_execution,
                event_type="autonomy.rollback.failed",
                message="Rollback nao suportado para este action type.",
                actor_user=requested_by,
            )
            AutonomousAuditService.create_incident(
                execution=autonomous_execution,
                incident_type="rollback_failed",
                summary="Rollback nao suportado para a autoexecucao selecionada.",
                severity="medium",
                payload={"action_type": action_type},
            )
            raise ValueError("Rollback nao suportado para este action type.")
        autonomous_execution.rollback_status = AutonomousExecution.RollbackStatus.EXECUTED
        autonomous_execution.execution_status = AutonomousExecution.ExecutionStatus.ROLLED_BACK
        autonomous_execution.save(update_fields=["rollback_status", "execution_status", "updated_at"])
        AutonomousAuditService.log_event(
            execution=autonomous_execution,
            event_type="autonomy.rollback.succeeded",
            message="Rollback executado com sucesso.",
            actor_user=requested_by,
        )
        return autonomous_execution
