from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.companies.models import Membership

from ..models import (
    AutomationTask,
    DeadLetterEvent,
    EventDelivery,
    EventSubscription,
    IntegrationEvent,
    IntegrationLog,
    ReactiveTriggerLog,
    WorkflowDefinition,
    WorkflowExecution,
)
from ..services.integration_service import (
    AutomationTaskService,
    EventDeliveryService,
    IntegrationEventService,
    WorkflowService,
)
from ..services.realtime_bus import RealtimeEventBus
from .serializers import (
    AutomationTaskSerializer,
    DeadLetterEventSerializer,
    EventDeliverySerializer,
    EventSubscriptionSerializer,
    IntegrationEventSerializer,
    IntegrationLogSerializer,
    ReactiveTriggerLogSerializer,
    WorkflowDefinitionSerializer,
    WorkflowExecutionSerializer,
)


class IntegrationBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def _accessible_company_ids(self):
        if getattr(self.request.user, "is_superuser", False):
            return None
        return list(Membership.objects.filter(user=self.request.user).values_list("company_id", flat=True))


class IntegrationEventViewSet(IntegrationBaseViewSet):
    queryset = IntegrationEvent.objects.prefetch_related("deliveries", "reactive_triggers").all()
    serializer_class = IntegrationEventSerializer
    filterset_fields = ("event_name", "source_module", "event_type", "status", "correlation_id", "priority", "company", "site")
    search_fields = ("event_name", "event_key", "aggregate_type", "aggregate_id", "correlation_id", "error_message", "request_id")
    ordering_fields = ("occurred_at", "published_at", "processed_at", "created_at")

    def get_queryset(self):
        queryset = super().get_queryset()
        company_ids = self._accessible_company_ids()
        if company_ids is None:
            return queryset
        return queryset.filter(company_id__in=company_ids)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        event = self.get_object()
        published_event = IntegrationEventService.publish_event(event=event)
        return Response(self.get_serializer(published_event).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def mark_processed(self, request, pk=None):
        event = self.get_object()
        processed_event = IntegrationEventService.mark_processed(event=event)
        return Response(self.get_serializer(processed_event).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def mark_failed(self, request, pk=None):
        event = self.get_object()
        failed_event = IntegrationEventService.mark_failed(
            event=event,
            error_message=request.data.get("error_message", "Processing failed."),
        )
        return Response(self.get_serializer(failed_event).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def chain(self, request, pk=None):
        event = self.get_object()
        chain = RealtimeEventBus.event_chain(event=event)
        return Response(self.get_serializer(chain, many=True).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def reprocess(self, request, pk=None):
        event = self.get_object()
        for delivery in event.deliveries.select_related("subscription"):
            if delivery.delivery_status in {EventDelivery.DeliveryStatus.FAILED, EventDelivery.DeliveryStatus.RETRYING, EventDelivery.DeliveryStatus.DEAD_LETTER}:
                EventDeliveryService.reprocess(delivery=delivery)
        event.refresh_from_db()
        return Response(self.get_serializer(event).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def intelligence_feed(self, request):
        queryset = self.get_queryset()
        company = queryset.filter(company_id=request.query_params.get("company")).first()
        site = queryset.filter(site_id=request.query_params.get("site")).first()
        if company is not None or site is not None:
            events = RealtimeEventBus.intelligence_feed(
                company=getattr(company, "company", None),
                site=getattr(site, "site", None),
                limit=int(request.query_params.get("limit", 20)),
            )
        else:
            events = list(queryset.filter(event_name__in=RealtimeEventBus.EVENT_STREAM_TYPES).order_by("-occurred_at", "-created_at")[: int(request.query_params.get("limit", 20))])
        return Response(self.get_serializer(events, many=True).data, status=status.HTTP_200_OK)


class EventSubscriptionViewSet(IntegrationBaseViewSet):
    queryset = EventSubscription.objects.all()
    serializer_class = EventSubscriptionSerializer
    filterset_fields = ("event_name", "target_module", "execution_mode", "is_active")
    search_fields = ("event_name", "target_module", "handler_name")
    ordering_fields = ("event_name", "target_module", "created_at")


class WorkflowDefinitionViewSet(IntegrationBaseViewSet):
    queryset = WorkflowDefinition.objects.all()
    serializer_class = WorkflowDefinitionSerializer
    filterset_fields = ("trigger_event_name", "workflow_type", "is_active")
    search_fields = ("name", "slug", "description", "trigger_event_name")
    ordering_fields = ("name", "created_at", "updated_at")


class WorkflowExecutionViewSet(IntegrationBaseViewSet):
    queryset = WorkflowExecution.objects.select_related("workflow_definition", "integration_event").all()
    serializer_class = WorkflowExecutionSerializer
    filterset_fields = ("workflow_definition", "integration_event", "status")
    search_fields = ("workflow_definition__name", "integration_event__event_name", "error_message")
    ordering_fields = ("started_at", "completed_at", "created_at")

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        execution = self.get_object()
        executed = WorkflowService.run_execution(execution=execution)
        return Response(self.get_serializer(executed).data, status=status.HTTP_200_OK)


class AutomationTaskViewSet(IntegrationBaseViewSet):
    queryset = AutomationTask.objects.all()
    serializer_class = AutomationTaskSerializer
    filterset_fields = ("task_type", "source_module", "target_module", "status", "correlation_id")
    search_fields = ("task_name", "correlation_id", "error_message")
    ordering_fields = ("scheduled_at", "started_at", "completed_at", "created_at")

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        task = self.get_object()
        updated = AutomationTaskService.transition(task=task, status=AutomationTask.Status.RUNNING)
        return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        task = self.get_object()
        updated = AutomationTaskService.transition(task=task, status=AutomationTask.Status.COMPLETED)
        return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def fail(self, request, pk=None):
        task = self.get_object()
        updated = AutomationTaskService.transition(
            task=task,
            status=AutomationTask.Status.FAILED,
            error_message=request.data.get("error_message", "Task failed."),
        )
        return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)


class IntegrationLogViewSet(IntegrationBaseViewSet):
    queryset = IntegrationLog.objects.all()
    serializer_class = IntegrationLogSerializer
    filterset_fields = ("source_module", "target_module", "event_name", "task_name", "log_level")
    search_fields = ("message", "event_name", "task_name")
    ordering_fields = ("created_at", "updated_at")


class DeadLetterEventViewSet(IntegrationBaseViewSet):
    queryset = DeadLetterEvent.objects.all()
    serializer_class = DeadLetterEventSerializer
    filterset_fields = ("original_event_name", "source_module")
    search_fields = ("original_event_name", "failure_reason")
    ordering_fields = ("moved_at", "created_at")


class EventDeliveryViewSet(IntegrationBaseViewSet):
    queryset = EventDelivery.objects.select_related("integration_event", "subscription").all()
    serializer_class = EventDeliverySerializer
    filterset_fields = ("subscriber_name", "delivery_status")
    search_fields = ("subscriber_name", "last_error", "integration_event__event_name")
    ordering_fields = ("created_at", "updated_at", "delivered_at")

    def get_queryset(self):
        queryset = super().get_queryset()
        company_ids = self._accessible_company_ids()
        if company_ids is None:
            return queryset
        return queryset.filter(integration_event__company_id__in=company_ids)

    @action(detail=True, methods=["post"])
    def reprocess(self, request, pk=None):
        delivery = self.get_object()
        EventDeliveryService.reprocess(delivery=delivery)
        delivery.refresh_from_db()
        return Response(self.get_serializer(delivery).data, status=status.HTTP_200_OK)


class ReactiveTriggerLogViewSet(IntegrationBaseViewSet):
    queryset = ReactiveTriggerLog.objects.select_related("integration_event").all()
    serializer_class = ReactiveTriggerLogSerializer
    filterset_fields = ("target_component", "trigger_type", "trigger_status")
    search_fields = ("summary", "integration_event__event_name", "target_component")
    ordering_fields = ("created_at", "updated_at")

    def get_queryset(self):
        queryset = super().get_queryset()
        company_ids = self._accessible_company_ids()
        if company_ids is None:
            return queryset
        return queryset.filter(integration_event__company_id__in=company_ids)
