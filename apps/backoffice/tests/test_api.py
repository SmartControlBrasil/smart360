from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User

from ..models import BackofficeAlert, BackofficeQueue, BackofficeTask, BackofficeWidget


class BackofficeApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="backoffice@smart360.local",
            password="StrongPass123",
            first_name="Backoffice",
        )
        self.client.force_authenticate(self.user)

    def test_create_queue_and_item(self):
        queue_response = self.client.post(
            reverse("backoffice-queues-list"),
            {
                "name": "Verificacoes Pendentes",
                "queue_type": "approval",
                "source_module": "trust_and_safety",
                "description": "Items waiting approval",
                "is_active": True,
                "ordering": 1,
            },
            format="json",
        )
        self.assertEqual(queue_response.status_code, status.HTTP_201_CREATED)
        queue_id = queue_response.data["id"]

        item_response = self.client.post(
            reverse("backoffice-queue-items-list"),
            {
                "queue": queue_id,
                "item_type": "provider_verification",
                "item_id": "PV-100",
                "reference_label": "Provider verification 100",
                "status": "pending",
                "priority": "high",
                "assigned_to": self.user.id,
            },
            format="json",
        )
        self.assertEqual(item_response.status_code, status.HTTP_201_CREATED)

    def test_create_alert_task_and_dashboard(self):
        BackofficeQueue.objects.create(name="Invoices Overdue", queue_type="billing", source_module="billing", ordering=1)
        BackofficeAlert.objects.create(
            title="Invoice overdue",
            alert_type="billing",
            source_module="billing",
            severity="critical",
            status="open",
            summary="Customer has overdue invoice",
        )
        BackofficeTask.objects.create(
            title="Review overdue invoice",
            task_type="review",
            source_module="billing",
            assigned_to=self.user,
            status="pending",
            priority="high",
        )
        BackofficeWidget.objects.create(
            name="Overdue Invoices Card",
            widget_type="metric_card",
            source_module="billing",
            title="Overdue invoices",
            config_json={"metric": "overdue_invoices"},
            is_active=True,
            ordering=1,
        )

        response = self.client.get(reverse("backoffice-dashboard"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("queues", response.data)
        self.assertIn("critical_alerts", response.data)
        self.assertIn("pending_tasks", response.data)
        self.assertIn("widgets", response.data)

