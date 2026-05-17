from datetime import date, timedelta

from django.utils import timezone

from apps.scheduling_center.models import (
    AvailabilitySlot,
    CalendarEvent,
    EventOccurrence,
    RecurrenceRule,
    RecurringEventLink,
    SchedulingTask,
)


class RecurrenceService:
    @staticmethod
    def _next_date(current_date: date, rule: RecurrenceRule) -> date:
        if rule.frequency_type == RecurrenceRule.FrequencyType.DAILY:
            return current_date + timedelta(days=rule.interval_value)
        if rule.frequency_type == RecurrenceRule.FrequencyType.WEEKLY:
            return current_date + timedelta(weeks=rule.interval_value)
        if rule.frequency_type == RecurrenceRule.FrequencyType.MONTHLY:
            return current_date + timedelta(days=30 * rule.interval_value)
        if rule.frequency_type == RecurrenceRule.FrequencyType.YEARLY:
            return current_date + timedelta(days=365 * rule.interval_value)
        return current_date + timedelta(days=rule.interval_value)

    @classmethod
    def generate_occurrences(cls, recurring_link: RecurringEventLink, count: int = 5):
        rule = recurring_link.recurrence_rule
        occurrences = []
        current_date = max(rule.start_date, recurring_link.parent_event.start_at.date())
        generated_count = 0

        while generated_count < count:
            if rule.end_date and current_date > rule.end_date:
                break
            if rule.occurrences_limit and generated_count >= rule.occurrences_limit:
                break

            occurrence, _ = EventOccurrence.objects.get_or_create(
                recurring_link=recurring_link,
                occurrence_date=current_date,
                defaults={"status": EventOccurrence.Status.GENERATED},
            )
            occurrences.append(occurrence)
            generated_count += 1
            current_date = cls._next_date(current_date, rule)

        return occurrences


class SchedulingDashboardService:
    @staticmethod
    def calendar_view(*, start_at=None, end_at=None, calendar_id=None, assigned_to=None):
        queryset = CalendarEvent.objects.select_related("calendar", "assigned_to").all()
        if start_at:
            queryset = queryset.filter(end_at__gte=start_at)
        if end_at:
            queryset = queryset.filter(start_at__lte=end_at)
        if calendar_id:
            queryset = queryset.filter(calendar_id=calendar_id)
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        return queryset.order_by("start_at")

    @staticmethod
    def upcoming_events(*, user=None, limit=10):
        queryset = CalendarEvent.objects.select_related("calendar", "assigned_to").filter(
            start_at__gte=timezone.now(),
            status__in=[
                CalendarEvent.Status.SCHEDULED,
                CalendarEvent.Status.CONFIRMED,
                CalendarEvent.Status.IN_PROGRESS,
            ],
        )
        if user is not None:
            queryset = queryset.filter(assigned_to=user)
        return queryset.order_by("start_at")[:limit]

    @staticmethod
    def my_tasks(*, user):
        return SchedulingTask.objects.filter(assigned_to=user).order_by("due_at", "-created_at")

    @staticmethod
    def availability(*, user_id=None, company_id=None, calendar_id=None, weekday=None):
        queryset = AvailabilitySlot.objects.select_related("user", "company", "calendar").all()
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if calendar_id:
            queryset = queryset.filter(calendar_id=calendar_id)
        if weekday is not None and weekday != "":
            queryset = queryset.filter(weekday=weekday)
        return queryset.order_by("weekday", "start_time")
