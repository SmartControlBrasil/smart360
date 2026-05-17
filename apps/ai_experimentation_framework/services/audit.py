from apps.ai_experimentation_framework.models import ExperimentAuditTrail
from apps.observability_center.services.observability_service import SystemEventService


class ExperimentAuditService:
    @staticmethod
    def log_event(*, experiment, event_type, message, variant=None, actor_user=None, payload=None):
        payload = payload or {}
        ExperimentAuditTrail.objects.create(
            experiment=experiment,
            variant=variant,
            actor_user=actor_user,
            event_type=event_type,
            message=message,
            payload=payload,
        )
        SystemEventService.log_system_event(
            event_type=event_type,
            source_module="ai_experimentation_framework",
            message=message,
            entity_type=experiment.target_component,
            entity_id=experiment.target_reference or str(experiment.public_id),
            user=actor_user,
            company=experiment.company,
            site=experiment.site,
            payload={
                "experiment_public_id": str(experiment.public_id),
                "variant_public_id": str(variant.public_id) if variant else "",
                **payload,
            },
        )

