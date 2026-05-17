from datetime import timedelta

import factory
from django.utils import timezone

from apps.scheduling_center.models import Calendar, CalendarEvent, SchedulingTask
from tests.factories.core import CompanyFactory, UserFactory


class CalendarFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Calendar

    name = factory.Sequence(lambda n: f"Calendar {n}")
    calendar_type = Calendar.CalendarType.OPERATIONAL
    description = factory.Faker("sentence")
    owner_user = factory.SubFactory(UserFactory)
    owner_company = factory.SubFactory(CompanyFactory)
    is_active = True


class CalendarEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CalendarEvent

    calendar = factory.SubFactory(CalendarFactory)
    title = factory.Sequence(lambda n: f"Calendar Event {n}")
    description = factory.Faker("sentence")
    event_type = CalendarEvent.EventType.MEETING
    status = CalendarEvent.Status.SCHEDULED
    start_at = factory.LazyFunction(timezone.now)
    end_at = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=1))
    is_all_day = False
    timezone = "America/Sao_Paulo"
    created_by = factory.SubFactory(UserFactory)
    assigned_to = factory.SubFactory(UserFactory)
    metadata = factory.LazyFunction(dict)


class SchedulingTaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SchedulingTask

    title = factory.Sequence(lambda n: f"Scheduling Task {n}")
    description = factory.Faker("sentence")
    task_type = SchedulingTask.TaskType.OPERATIONAL
    priority = SchedulingTask.Priority.MEDIUM
    status = SchedulingTask.Status.PENDING
    due_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=1))
    assigned_to = factory.SubFactory(UserFactory)
    created_by = factory.SubFactory(UserFactory)

