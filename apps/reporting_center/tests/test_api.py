from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User

from ..models import ExportExecution, ReportArtifact, ReportRequest


class ReportingCenterApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="reporting@smart360.local",
            password="StrongPass123",
            first_name="Reporting",
        )
        self.client.force_authenticate(self.user)

    def test_run_report_creates_artifact(self):
        template_response = self.client.post(
            reverse("reporting-templates-list"),
            {
                "name": "Service Orders Summary",
                "source_module": "smart_system",
                "report_type": "operational",
                "output_format_default": "json",
                "config_json": {"dataset": "service_orders"},
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(template_response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse("reporting-run-report"),
            {
                "template": template_response.data["id"],
                "source_module": "smart_system",
                "status": "pending",
                "output_format": "json",
                "filters_json": {"status": "open"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ReportRequest.objects.exists())
        self.assertTrue(ReportArtifact.objects.exists())

    def test_run_export_marks_execution_completed(self):
        profile_response = self.client.post(
            reverse("reporting-export-profiles-list"),
            {
                "name": "Export Leads JSON",
                "source_module": "growth_engine",
                "export_type": "analytical",
                "columns_config": ["company_name", "city", "status"],
                "filters_config": {"status": "new"},
                "is_active": True,
                "created_by": self.user.id,
            },
            format="json",
        )
        self.assertEqual(profile_response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse("reporting-run-export"),
            {
                "export_profile": profile_response.data["id"],
                "status": "pending",
                "output_format": "json",
                "filters_json": {"city": "Campinas"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        execution = ExportExecution.objects.get(id=response.data["id"])
        self.assertEqual(execution.status, ExportExecution.Status.COMPLETED)

    def test_history_endpoints(self):
        report_history_response = self.client.get(reverse("reporting-report-history"))
        export_history_response = self.client.get(reverse("reporting-export-history"))
        self.assertEqual(report_history_response.status_code, status.HTTP_200_OK)
        self.assertEqual(export_history_response.status_code, status.HTTP_200_OK)

