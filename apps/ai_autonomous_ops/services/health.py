from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.ai_autonomous_ops.models import AutonomousExecution, AutonomousIncident


class AutonomousHealthService:
    @classmethod
    def summary(cls, *, company=None):
        executions = AutonomousExecution.objects.all()
        incidents = AutonomousIncident.objects.all()
        if company is not None:
            executions = executions.filter(company=company)
            incidents = incidents.filter(company=company)
        total_executions = executions.count()
        succeeded = executions.filter(execution_status=AutonomousExecution.ExecutionStatus.SUCCEEDED).count()
        rolled_back = executions.filter(rollback_status=AutonomousExecution.RollbackStatus.EXECUTED).count()
        blocked = executions.filter(execution_status=AutonomousExecution.ExecutionStatus.BLOCKED).count()
        return {
            "total_executions": total_executions,
            "success_count": succeeded,
            "success_rate": round((succeeded / total_executions) * 100, 2) if total_executions else 0,
            "rollback_count": rolled_back,
            "rollback_rate": round((rolled_back / total_executions) * 100, 2) if total_executions else 0,
            "blocked_count": blocked,
            "blocked_rate": round((blocked / total_executions) * 100, 2) if total_executions else 0,
            "average_confidence": float(executions.aggregate(avg=Avg("confidence_score"))["avg"] or 0),
            "recent_incidents": incidents.order_by("-created_at")[:6],
            "by_agent": list(executions.values("source_agent").annotate(total=Count("id")).order_by("-total")[:8]),
            "by_tenant": list(executions.values("company__name").annotate(total=Count("id")).order_by("-total")[:8]),
        }
