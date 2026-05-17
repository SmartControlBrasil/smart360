from apps.ai_autonomous_ops.models import AutonomousAuditTrail, AutonomousIncident
from apps.observability_center.services.observability_service import SystemEventService


class AutonomousAuditService:
    @staticmethod
    def log_event(*, execution, event_type, message, actor_user=None, payload=None):
        payload = payload or {}
        AutonomousAuditTrail.objects.create(
            autonomous_execution=execution,
            actor_user=actor_user,
            event_type=event_type,
            message=message,
            payload=payload,
        )
        SystemEventService.log_system_event(
            event_type=event_type,
            source_module="ai_autonomous_ops",
            message=message,
            entity_type=execution.action_type,
            entity_id=str(execution.public_id),
            user=actor_user,
            company=execution.company,
            site=execution.site,
            payload={
                "autonomous_execution_public_id": str(execution.public_id),
                "action_type": execution.action_type,
                "source_agent": execution.source_agent,
                "confidence": str(execution.confidence_score),
                **payload,
            },
        )

    @staticmethod
    def create_incident(*, execution, incident_type, summary, severity="medium", payload=None):
        incident = AutonomousIncident.objects.create(
            company=execution.company,
            site=execution.site,
            autonomous_execution=execution,
            severity=severity,
            incident_type=incident_type,
            summary=summary,
            payload=payload or {},
        )
        SystemEventService.log_system_event(
            event_type="autonomy.incident.created",
            source_module="ai_autonomous_ops",
            message=summary,
            severity="error" if severity in {"high", "critical"} else "warning",
            entity_type=execution.action_type,
            entity_id=str(execution.public_id),
            company=execution.company,
            site=execution.site,
            payload={"incident_public_id": str(incident.public_id), "incident_type": incident_type},
        )
        return incident

