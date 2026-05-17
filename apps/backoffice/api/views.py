from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import (
    BackofficeAlert,
    BackofficeNote,
    BackofficeQueue,
    BackofficeQueueItem,
    BackofficeQuickAction,
    BackofficeTask,
    BackofficeWidget,
)
from ..services.backoffice_service import BackofficeDashboardService
from .serializers import (
    BackofficeAlertSerializer,
    BackofficeNoteSerializer,
    BackofficeQueueItemSerializer,
    BackofficeQueueSerializer,
    BackofficeQuickActionSerializer,
    BackofficeTaskSerializer,
    BackofficeWidgetSerializer,
)


class BackofficeBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class BackofficeQueueViewSet(BackofficeBaseViewSet):
    queryset = BackofficeQueue.objects.all()
    serializer_class = BackofficeQueueSerializer
    filterset_fields = ("queue_type", "source_module", "is_active")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("ordering", "name", "updated_at")


class BackofficeQueueItemViewSet(BackofficeBaseViewSet):
    queryset = BackofficeQueueItem.objects.select_related("queue", "assigned_to").all()
    serializer_class = BackofficeQueueItemSerializer
    filterset_fields = ("queue", "item_type", "status", "priority", "assigned_to")
    search_fields = ("reference_label", "item_type", "item_id")
    ordering_fields = ("created_at", "updated_at", "due_at")


class BackofficeAlertViewSet(BackofficeBaseViewSet):
    queryset = BackofficeAlert.objects.all()
    serializer_class = BackofficeAlertSerializer
    filterset_fields = ("alert_type", "source_module", "severity", "status")
    search_fields = ("title", "slug", "summary", "details", "related_item_type", "related_item_id")
    ordering_fields = ("created_at", "updated_at", "resolved_at")


class BackofficeTaskViewSet(BackofficeBaseViewSet):
    queryset = BackofficeTask.objects.select_related("assigned_to").all()
    serializer_class = BackofficeTaskSerializer
    filterset_fields = ("task_type", "source_module", "assigned_to", "status", "priority")
    search_fields = ("title", "related_item_type", "related_item_id", "notes")
    ordering_fields = ("created_at", "updated_at", "due_at", "completed_at")


class BackofficeQuickActionViewSet(BackofficeBaseViewSet):
    queryset = BackofficeQuickAction.objects.all()
    serializer_class = BackofficeQuickActionSerializer
    filterset_fields = ("target_module", "action_type", "is_active")
    search_fields = ("name", "slug", "label", "route_path")
    ordering_fields = ("ordering", "label", "updated_at")


class BackofficeWidgetViewSet(BackofficeBaseViewSet):
    queryset = BackofficeWidget.objects.all()
    serializer_class = BackofficeWidgetSerializer
    filterset_fields = ("widget_type", "source_module", "is_active")
    search_fields = ("name", "slug", "title")
    ordering_fields = ("ordering", "title", "updated_at")


class BackofficeNoteViewSet(BackofficeBaseViewSet):
    queryset = BackofficeNote.objects.select_related("created_by").all()
    serializer_class = BackofficeNoteSerializer
    filterset_fields = ("note_type", "related_item_type", "created_by", "is_private")
    search_fields = ("related_item_type", "related_item_id", "content")
    ordering_fields = ("created_at", "updated_at")


class BackofficeDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(BackofficeDashboardService.build_dashboard())

