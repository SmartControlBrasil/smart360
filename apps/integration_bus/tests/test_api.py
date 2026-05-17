from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User

from ..models import AutomationTask, DeadLetterEvent, IntegrationEvent, WorkflowExecution


class IntegrationBusApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="integration@smart360.local",
            password="StrongPass123",
            first_name="Integration",
        )
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save(update_fields=["is_staff", "is_superuser"])
        self.client.force_authenticate(self.user)

    def test_publish_event_creates_workflow_execution(self):
        workflow_response = self.client.post(
            reverse("integration-workflow-definitions-list"),
            {
                "name": "Service Order Completion Analytics",
                "description": "Generate analytics tasks on service order completion",
                "trigger_event_name": "service_order_completed",
                "workflow_type": "automation",
                "config_json": {
                    "automation_tasks": [
                        {
                            "task_name": "create_analytics_metric",
                            "task_type": "metric",
                            "target_module": "analytics_platform",
                            "payload": {"metric_name": "completed_service_orders"},
                        }
                    ]
                },
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(workflow_response.status_code, status.HTTP_201_CREATED)

        event_response = self.client.post(
            reverse("integration-events-list"),
            {
                "event_name": "service_order_completed",
                "source_module": "smart_system",
                "event_type": "integration",
                "aggregate_type": "service_order",
                "aggregate_id": "SO-20260311-0010",
                "payload": {"status": "completed"},
                "correlation_id": "corr-service-order-0010",
            },
            format="json",
        )
        self.assertEqual(event_response.status_code, status.HTTP_201_CREATED)
        event = IntegrationEvent.objects.get(event_name="service_order_completed")

        publish_response = self.client.post(
            reverse("integration-events-publish", args=[event.id]),
            {},
            format="json",
        )
        self.assertEqual(publish_response.status_code, status.HTTP_200_OK)
        self.assertTrue(WorkflowExecution.objects.filter(integration_event=event).exists())

    def test_run_workflow_execution_generates_task(self):
        workflow_definition = self.client.post(
            reverse("integration-workflow-definitions-list"),
            {
                "name": "Technician Assignment Accepted Notification",
                "trigger_event_name": "technician_assignment_accepted",
                "workflow_type": "automation",
                "config_json": {
                    "automation_tasks": [
                        {
                            "task_name": "notify_assignment",
                            "task_type": "notification",
                            "target_module": "marketplace_technicians",
                        }
                    ]
                },
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(workflow_definition.status_code, status.HTTP_201_CREATED)

        event = IntegrationEvent.objects.create(
            event_name="technician_assignment_accepted",
            source_module="marketplace_technicians",
            event_type=IntegrationEvent.EventType.INTEGRATION,
            correlation_id="corr-tech-accepted-1",
        )
        execution = WorkflowExecution.objects.create(
            workflow_definition_id=workflow_definition.data["id"],
            integration_event=event,
        )

        run_response = self.client.post(
            reverse("integration-workflow-executions-run", args=[execution.id]),
            {},
            format="json",
        )
        self.assertEqual(run_response.status_code, status.HTTP_200_OK)
        self.assertTrue(AutomationTask.objects.filter(task_name="notify_assignment").exists())

    def test_failed_event_moves_to_dead_letter_after_retries(self):
        event = IntegrationEvent.objects.create(
            event_name="site_delivered",
            source_module="smart_site_factory",
            event_type=IntegrationEvent.EventType.INTEGRATION,
            correlation_id="corr-site-delivered-1",
        )

        for _ in range(3):
            response = self.client.post(
                reverse("integration-events-mark-failed", args=[event.id]),
                {"error_message": "downstream timeout"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        event.refresh_from_db()
        self.assertEqual(event.status, IntegrationEvent.Status.DEAD_LETTER)
        self.assertTrue(DeadLetterEvent.objects.filter(original_event_name="site_delivered").exists())
