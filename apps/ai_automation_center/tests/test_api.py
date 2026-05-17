from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User

from ..models import AITaskType, AutomationExecution, PromptVersion


class AIAutomationCenterApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="ai@smart360.local",
            password="StrongPass123",
            first_name="AI",
        )
        self.client.force_authenticate(self.user)
        self.task_type = AITaskType.objects.create(
            name="Text Summarization",
            task_category=AITaskType.TaskCategory.SUMMARIZATION,
            is_active=True,
        )

    def test_create_prompt_template_creates_version_snapshot(self):
        response = self.client.post(
            reverse("ai-prompt-templates-list"),
            {
                "name": "Lead Summary Prompt",
                "task_type": self.task_type.id,
                "source_module": "growth_engine",
                "prompt_template": "Summarize {{lead_name}} and suggest next action.",
                "expected_output_schema": {"summary": "string"},
                "model_hint": "gpt-style-chat-model",
                "version_label": "v1",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PromptVersion.objects.count(), 1)

    def test_run_task_creates_execution_and_artifact(self):
        prompt_response = self.client.post(
            reverse("ai-prompt-templates-list"),
            {
                "name": "OS Summary Prompt",
                "task_type": self.task_type.id,
                "source_module": "smart_system",
                "prompt_template": "Summarize service order {{os_number}}",
                "version_label": "v1",
                "is_active": True,
            },
            format="json",
        )
        response = self.client.post(
            reverse("ai-run-task"),
            {
                "task_type": self.task_type.id,
                "prompt_template": prompt_response.data["id"],
                "source_module": "smart_system",
                "source_reference_type": "service_order",
                "source_reference_id": "SO-123",
                "input_payload": {"os_number": "SO-123"},
                "priority": "high",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["task_request"]["status"], "completed")
        self.assertEqual(response.data["execution"]["status"], "completed")

    def test_run_automation_rule(self):
        prompt_response = self.client.post(
            reverse("ai-prompt-templates-list"),
            {
                "name": "Site Copy Prompt",
                "task_type": self.task_type.id,
                "source_module": "smart_site_factory",
                "prompt_template": "Generate copy for {{business_name}}",
                "version_label": "v1",
                "is_active": True,
            },
            format="json",
        )
        rule_response = self.client.post(
            reverse("ai-automation-rules-list"),
            {
                "name": "Generate Site Copy",
                "source_module": "smart_site_factory",
                "trigger_event": "site_order_created",
                "task_type": self.task_type.id,
                "prompt_template": prompt_response.data["id"],
                "is_active": True,
                "priority": "medium",
                "config_json": {"business_name": "Acme"},
            },
            format="json",
        )
        response = self.client.post(
            reverse("ai-automation-rules-run", args=[rule_response.data["id"]]),
            {
                "source_reference_type": "site_order",
                "source_reference_id": "SITE-10",
                "integration_event_id": "evt-10",
                "input_payload": {"business_name": "Acme"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AutomationExecution.objects.count(), 1)

