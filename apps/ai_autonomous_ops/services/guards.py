from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from apps.ai_autonomous_ops.models import AutonomousExecution, AutonomousExecutionGuard, AutonomousIncident, AutonomousModeConfig


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    reason: str
    payload: dict


class AutonomousGuardService:
    @classmethod
    def evaluate(cls, *, config: AutonomousModeConfig, decision, confidence_score):
        now = timezone.now()
        hour_start = now - timedelta(hours=1)
        day_start = now - timedelta(days=1)
        executions = AutonomousExecution.objects.filter(company=config.company or decision.company)
        executions_by_action = executions.filter(action_type=decision.normalized_action_type)
        failures = executions.filter(execution_status=AutonomousExecution.ExecutionStatus.FAILED, created_at__gte=day_start)
        rollbacks = executions.filter(rollback_status=AutonomousExecution.RollbackStatus.EXECUTED, created_at__gte=day_start)
        open_incidents = AutonomousIncident.objects.filter(company=config.company or decision.company, status=AutonomousIncident.Status.OPEN)
        if executions.filter(created_at__gte=hour_start).count() >= config.max_executions_per_hour:
            return GuardResult(False, "Guard de volume horario excedido.", {"guard": "max_executions_per_hour"})
        if executions.filter(created_at__gte=day_start).count() >= config.max_executions_per_day:
            return GuardResult(False, "Guard de volume diario excedido.", {"guard": "max_executions_per_day"})
        if failures.count() >= config.max_failures_per_day:
            return GuardResult(False, "Guard de falha diaria excedido.", {"guard": "max_failures_per_day"})
        if rollbacks.count() >= config.max_rollbacks_per_day:
            return GuardResult(False, "Guard de rollback diario excedido.", {"guard": "max_rollbacks_per_day"})
        if open_incidents.filter(severity__in=["high", "critical"]).exists():
            return GuardResult(False, "Incidente aberto de autonomia em severidade alta.", {"guard": "open_high_incident"})
        if decision.agent_action_proposal.agent_run.agent.slug in (config.kill_switch_agents or []):
            return GuardResult(False, "Kill switch por agente ativo.", {"guard": "agent_kill_switch"})
        if decision.normalized_action_type in (config.kill_switch_action_types or []):
            return GuardResult(False, "Kill switch por action type ativo.", {"guard": "action_kill_switch"})
        if float(confidence_score) < 0.60:
            return GuardResult(False, "Confidence score abaixo do minimo absoluto do guard.", {"guard": "confidence_floor"})
        custom_guard = AutonomousExecutionGuard.objects.filter(company=config.company, enabled=True, guard_type=AutonomousExecutionGuard.GuardType.CONFIDENCE, threshold_key=decision.normalized_action_type).first()
        if custom_guard and float(confidence_score) < float(custom_guard.threshold_value):
            return GuardResult(False, "Confidence abaixo do threshold guard customizado.", {"guard": "custom_confidence"})
        return GuardResult(True, "Guards aprovados.", {"guard": "passed"})

