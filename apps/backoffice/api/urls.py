from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    BackofficeAlertViewSet,
    BackofficeDashboardView,
    BackofficeNoteViewSet,
    BackofficeQueueItemViewSet,
    BackofficeQueueViewSet,
    BackofficeQuickActionViewSet,
    BackofficeTaskViewSet,
    BackofficeWidgetViewSet,
)

router = DefaultRouter()
router.register("queues", BackofficeQueueViewSet, basename="backoffice-queues")
router.register("queue-items", BackofficeQueueItemViewSet, basename="backoffice-queue-items")
router.register("alerts", BackofficeAlertViewSet, basename="backoffice-alerts")
router.register("tasks", BackofficeTaskViewSet, basename="backoffice-tasks")
router.register("quick-actions", BackofficeQuickActionViewSet, basename="backoffice-quick-actions")
router.register("widgets", BackofficeWidgetViewSet, basename="backoffice-widgets")
router.register("notes", BackofficeNoteViewSet, basename="backoffice-notes")

urlpatterns = router.urls + [
    path("dashboard/", BackofficeDashboardView.as_view(), name="backoffice-dashboard"),
]

