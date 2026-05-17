from __future__ import annotations

from apps.access_control_center.models import AccessAuditLog
from apps.access_control_center.services.access_service import AccessAuditService
from apps.ai_decision_engine.models import AgentDecision, DecisionAuditTrail


class DecisionAuditService:
    @staticmethod
    def log_event(
        *,
        decision: AgentDecision,
        event_type: str,
        message: str,
        actor_mode: str = DecisionAuditTrail.ActorMode.SYSTEM,
        actor_user=None,
        actor_label: str = "",
        metadata: dict | None = None,
    ):
        return DecisionAuditTrail.objects.create(
            decision=decision,
            event_type=event_type,
            actor_mode=actor_mode,
            actor_user=actor_user,
            actor_label=actor_label,
            message=message,
            metadata=metadata or {},
        )

    @staticmethod
    def log_access(
        *,
        decision: AgentDecision,
        user,
        action: str,
        decision_outcome: str,
        reason: str,
        metadata: dict | None = None,
    ):
        return AccessAuditService.log(
            user=user,
            action=action,
            domain="ai_agents_admin",
            decision=decision_outcome,
            reason=reason,
            resource_type=decision.target_entity or decision.normalized_action_type,
            resource_id=decision.target_entity_id or str(decision.public_id),
            company=decision.company,
            site=decision.site,
            metadata=metadata or {},
        )


ALLOW = AccessAuditLog.Decision.ALLOW
DENY = AccessAuditLog.Decision.DENY

