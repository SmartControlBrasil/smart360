from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company
from apps.users.models import User

from ..models import Calendar, CalendarEvent, RecurrenceRule


class SchedulingCenterApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="scheduling@smart360.local",
            password="StrongPass123",
            first_name="Scheduling",
        )
        self.company = Company.objects.create(
            name="Scheduling Co",
            slug="scheduling-co",
            status=Company.Status.ACTIVE,
        )
        self.client.force_authenticate(self.user)

    def test_create_event_and_list_upcoming(self):
        calendar = Calendar.objects.create(
            name="Agenda Operacional",
            calendar_type=Calendar.CalendarType.OPERATIONAL,
            owner_company=self.company,
        )
        CalendarEvent.objects.create(
            calendar=calendar,
            title="Visita tecnica",
            event_type=CalendarEvent.EventType.VISIT,
            status=CalendarEvent.Status.CONFIRMED,
            start_at=timezone.now() + timedelta(hours=3),
            end_at=timezone.now() + timedelta(hours=4),
            assigned_to=self.user,
        )

        response = self.client.get(reverse("scheduling-upcoming-events"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_generate_occurrences_for_recurring_link(self):
        calendar = Calendar.objects.create(
            name="Agenda Producao",
            calendar_type=Calendar.CalendarType.PRODUCTION,
            owner_company=self.company,
        )
        event = CalendarEvent.objects.create(
            calendar=calendar,
            title="Preventiva recorrente",
            event_type=CalendarEvent.EventType.PREVENTIVE,
            status=CalendarEvent.Status.SCHEDULED,
            start_at=timezone.now() + timedelta(days=1),
            end_at=timezone.now() + timedelta(days=1, hours=1),
            assigned_to=self.user,
        )
        rule = RecurrenceRule.objects.create(
            name="Semanal",
            frequency_type=RecurrenceRule.FrequencyType.WEEKLY,
            interval_value=1,
            start_date=(timezone.now() + timedelta(days=1)).date(),
            occurrences_limit=3,
        )
        link_response = self.client.post(
            reverse("scheduling-recurring-links-list"),
            {"parent_event": event.id, "recurrence_rule": rule.id, "is_active": True},
            format="json",
        )
        self.assertEqual(link_response.status_code, status.HTTP_201_CREATED)

        generate_response = self.client.post(
            reverse("scheduling-recurring-links-generate-occurrences", args=[link_response.data["id"]]),
            {"count": 3},
            format="json",
        )
        self.assertEqual(generate_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(generate_response.data), 3)

    def test_my_tasks_endpoint(self):
        response = self.client.post(
            reverse("scheduling-tasks-list"),
            {
                "title": "Revisar agenda da semana",
                "task_type": "review",
                "priority": "high",
                "status": "pending",
                "due_at": (timezone.now() + timedelta(days=1)).isoformat(),
                "assigned_to": self.user.id,
                "created_by": self.user.id,
                "related_module": "backoffice",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(reverse("scheduling-my-tasks"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

