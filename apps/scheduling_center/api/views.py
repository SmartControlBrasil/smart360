from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.scheduling_center.api.serializers import (
    AvailabilitySlotSerializer,
    CalendarEventSerializer,
    CalendarSerializer,
    EventOccurrenceSerializer,
    EventParticipantSerializer,
    RecurrenceRuleSerializer,
    RecurringEventLinkSerializer,
    ScheduledReminderSerializer,
    SchedulingTaskSerializer,
)
from apps.scheduling_center.models import (
    AvailabilitySlot,
    Calendar,
    CalendarEvent,
    EventOccurrence,
    EventParticipant,
    RecurrenceRule,
    RecurringEventLink,
    ScheduledReminder,
    SchedulingTask,
)
from apps.scheduling_center.services.scheduling_service import (
    RecurrenceService,
    SchedulingDashboardService,
)


class SchedulingBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class CalendarViewSet(SchedulingBaseViewSet):
    queryset = Calendar.objects.select_related("owner_user", "owner_company").all()
    serializer_class = CalendarSerializer
    filterset_fields = ("calendar_type", "owner_user", "owner_company", "is_active")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "updated_at")


class CalendarEventViewSet(SchedulingBaseViewSet):
    queryset = CalendarEvent.objects.select_related("calendar", "created_by", "assigned_to").all()
    serializer_class = CalendarEventSerializer
    filterset_fields = ("calendar", "event_type", "status", "is_all_day", "related_module", "assigned_to")
    search_fields = ("title", "description", "location", "related_item_type", "related_item_id")
    ordering_fields = ("start_at", "end_at", "updated_at")


class EventParticipantViewSet(SchedulingBaseViewSet):
    queryset = EventParticipant.objects.select_related("calendar_event", "user", "company").all()
    serializer_class = EventParticipantSerializer
    filterset_fields = ("calendar_event", "user", "company", "participant_type", "response_status")
    search_fields = ("calendar_event__title", "user__email", "company__name", "notes")
    ordering_fields = ("created_at", "updated_at")


class RecurrenceRuleViewSet(SchedulingBaseViewSet):
    queryset = RecurrenceRule.objects.all()
    serializer_class = RecurrenceRuleSerializer
    filterset_fields = ("frequency_type", "is_active")
    search_fields = ("name", "slug")
    ordering_fields = ("name", "start_date", "updated_at")


class RecurringEventLinkViewSet(SchedulingBaseViewSet):
    queryset = RecurringEventLink.objects.select_related("parent_event", "recurrence_rule").all()
    serializer_class = RecurringEventLinkSerializer
    filterset_fields = ("parent_event", "recurrence_rule", "is_active")
    search_fields = ("parent_event__title", "recurrence_rule__name")
    ordering_fields = ("created_at", "updated_at")

    @action(detail=True, methods=["post"], url_path="generate-occurrences")
    def generate_occurrences(self, request, pk=None):
        recurring_link = self.get_object()
        count = int(request.data.get("count", 5))
        occurrences = RecurrenceService.generate_occurrences(recurring_link, count=count)
        serializer = EventOccurrenceSerializer(occurrences, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EventOccurrenceViewSet(SchedulingBaseViewSet):
    queryset = EventOccurrence.objects.select_related("recurring_link", "calendar_event").all()
    serializer_class = EventOccurrenceSerializer
    filterset_fields = ("recurring_link", "calendar_event", "status", "occurrence_date")
    search_fields = ("notes", "recurring_link__parent_event__title")
    ordering_fields = ("occurrence_date", "generated_at", "updated_at")


class AvailabilitySlotViewSet(SchedulingBaseViewSet):
    queryset = AvailabilitySlot.objects.select_related("user", "company", "calendar").all()
    serializer_class = AvailabilitySlotSerializer
    filterset_fields = ("user", "company", "calendar", "weekday", "slot_type", "is_available")
    search_fields = ("user__email", "company__name", "calendar__name", "notes")
    ordering_fields = ("weekday", "start_time", "updated_at")


class ScheduledReminderViewSet(SchedulingBaseViewSet):
    queryset = ScheduledReminder.objects.select_related("calendar_event").all()
    serializer_class = ScheduledReminderSerializer
    filterset_fields = ("calendar_event", "reminder_type", "channel", "status")
    search_fields = ("calendar_event__title",)
    ordering_fields = ("remind_at", "created_at", "updated_at")


class SchedulingTaskViewSet(SchedulingBaseViewSet):
    queryset = SchedulingTask.objects.select_related("assigned_to", "created_by").all()
    serializer_class = SchedulingTaskSerializer
    filterset_fields = ("task_type", "priority", "status", "assigned_to", "related_module")
    search_fields = ("title", "description", "related_item_type", "related_item_id")
    ordering_fields = ("due_at", "created_at", "updated_at", "completed_at")


class CalendarViewEndpoint(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        start_at = request.query_params.get("start_at")
        end_at = request.query_params.get("end_at")
        calendar_id = request.query_params.get("calendar")
        assigned_to = request.query_params.get("assigned_to")
        queryset = SchedulingDashboardService.calendar_view(
            start_at=start_at,
            end_at=end_at,
            calendar_id=calendar_id,
            assigned_to=assigned_to,
        )
        serializer = CalendarEventSerializer(queryset, many=True)
        return Response({"count": len(serializer.data), "results": serializer.data})


class UpcomingEventsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        queryset = SchedulingDashboardService.upcoming_events(user=request.user, limit=10)
        serializer = CalendarEventSerializer(queryset, many=True)
        return Response({"count": len(serializer.data), "results": serializer.data})


class MyTasksView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        queryset = SchedulingDashboardService.my_tasks(user=request.user)
        serializer = SchedulingTaskSerializer(queryset, many=True)
        return Response({"count": len(serializer.data), "results": serializer.data})


class AvailabilityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        queryset = SchedulingDashboardService.availability(
            user_id=request.query_params.get("user"),
            company_id=request.query_params.get("company"),
            calendar_id=request.query_params.get("calendar"),
            weekday=request.query_params.get("weekday"),
        )
        serializer = AvailabilitySlotSerializer(queryset, many=True)
        return Response({"count": len(serializer.data), "results": serializer.data})

