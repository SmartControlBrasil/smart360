from apps.ai_simulation_engine.models import SimulationAuditTrail, SimulationRun


class SimulationAuditService:
    @staticmethod
    def log_event(*, simulation_run: SimulationRun, event_type: str, message: str, actor_user=None, payload=None):
        return SimulationAuditTrail.objects.create(
            simulation_run=simulation_run,
            event_type=event_type,
            actor_user=actor_user,
            message=message,
            payload=payload or {},
        )

