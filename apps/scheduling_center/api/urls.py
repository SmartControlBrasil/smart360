from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.scheduling_center.api.views import (
    AvailabilitySlotViewSet,
    AvailabilityView,
    CalendarEventViewSet,
    CalendarViewEndpoint,
    CalendarViewSet,
    EventOccurrenceViewSet,
    EventParticipantViewSet,
    MyTasksView,
    RecurrenceRuleViewSet,
    RecurringEventLinkViewSet,
    ScheduledReminderViewSet,
    SchedulingTaskViewSet,
    UpcomingEventsView,
)

router = DefaultRouter()
router.register("calendars", CalendarViewSet, basename="scheduling-calendars")
router.register("events", CalendarEventViewSet, basename="scheduling-events")
router.register("participants", EventParticipantViewSet, basename="scheduling-participants")
router.register("recurrence-rules", RecurrenceRuleViewSet, basename="scheduling-recurrence-rules")
router.register("recurring-links", RecurringEventLinkViewSet, basename="scheduling-recurring-links")
router.register("occurrences", EventOccurrenceViewSet, basename="scheduling-occurrences")
router.register("availability-slots", AvailabilitySlotViewSet, basename="scheduling-availability-slots")
router.register("reminders", ScheduledReminderViewSet, basename="scheduling-reminders")
router.register("tasks", SchedulingTaskViewSet, basename="scheduling-tasks")

urlpatterns = router.urls + [
    path("calendar-view/", CalendarViewEndpoint.as_view(), name="scheduling-calendar-view"),
    path("upcoming-events/", UpcomingEventsView.as_view(), name="scheduling-upcoming-events"),
    path("my-tasks/", MyTasksView.as_view(), name="scheduling-my-tasks"),
    path("availability/", AvailabilityView.as_view(), name="scheduling-availability"),
]

