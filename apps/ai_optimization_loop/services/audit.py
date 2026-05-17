from apps.ai_optimization_loop.models import OptimizationAuditTrail


class OptimizationAuditService:
    @staticmethod
    def log_event(*, event_type, message, actor_user=None, proposal=None, payload=None):
        return OptimizationAuditTrail.objects.create(
            proposal=proposal,
            actor_user=actor_user,
            event_type=event_type,
            message=message,
            payload=payload or {},
        )

