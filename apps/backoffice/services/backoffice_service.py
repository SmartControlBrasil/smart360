from django.db.models import Count

from ..models import (
    BackofficeAlert,
    BackofficeQueue,
    BackofficeQuickAction,
    BackofficeTask,
    BackofficeWidget,
)


class BackofficeDashboardService:
    @staticmethod
    def build_dashboard():
        queues = list(
            BackofficeQueue.objects.filter(is_active=True)
            .annotate(items_count=Count("items"))
            .values("public_id", "name", "slug", "queue_type", "source_module", "items_count", "ordering")
            .order_by("ordering", "name")
        )
        critical_alerts = list(
            BackofficeAlert.objects.filter(
                severity=BackofficeAlert.Severity.CRITICAL,
                status__in=[BackofficeAlert.Status.OPEN, BackofficeAlert.Status.ACKNOWLEDGED],
            )
            .values("public_id", "title", "source_module", "severity", "status", "summary", "created_at")
            .order_by("-created_at")[:10]
        )
        pending_tasks = list(
            BackofficeTask.objects.filter(
                status__in=[BackofficeTask.Status.PENDING, BackofficeTask.Status.IN_PROGRESS, BackofficeTask.Status.BLOCKED]
            )
            .values("public_id", "title", "task_type", "source_module", "priority", "status", "due_at")
            .order_by("-created_at")[:10]
        )
        widgets = list(
            BackofficeWidget.objects.filter(is_active=True)
            .values("public_id", "name", "slug", "widget_type", "source_module", "title", "config_json", "ordering")
            .order_by("ordering", "title")
        )
        quick_actions = list(
            BackofficeQuickAction.objects.filter(is_active=True)
            .values("public_id", "name", "slug", "target_module", "action_type", "label", "route_path", "ordering")
            .order_by("ordering", "label")
        )
        return {
            "queues": queues,
            "critical_alerts": critical_alerts,
            "pending_tasks": pending_tasks,
            "widgets": widgets,
            "quick_actions": quick_actions,
        }

