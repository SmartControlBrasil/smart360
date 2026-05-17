from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.access_control_center.models import AccessAuditLog
from apps.access_control_center.services.access_service import AccessAuditService
from apps.companies.models import Company
from apps.observability_center.models import ErrorIncident, JobExecutionTrace, MetricCounter, RequestTrace, SystemEventLog
from apps.observability_center.services.observability_service import (
    ErrorIncidentService,
    JobExecutionTraceService,
    MetricCounterService,
    SystemEventService,
)
from apps.users.models import User


class ObservabilityApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(
            email="observability-admin@smart360.local",
            password="admin123!",
            first_name="Observability",
            last_name="Admin",
        )

    def setUp(self):
        self.client.force_authenticate(self.user)

    def test_health_summary_responds(self):
        response = self.client.get(reverse("observability-health-summary"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("checks", response.data)

    def test_health_live_generates_request_id_and_trace(self):
        response = self.client.get("/health/live/", HTTP_X_REQUEST_ID="req-observability-001")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["X-Request-ID"], "req-observability-001")
        self.assertTrue(RequestTrace.objects.filter(request_id="req-observability-001", path="/health/live/").exists())

    def test_platform_summary_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(reverse("observability-platform-summary"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_system_event_service_creates_event(self):
        SystemEventService.log_system_event(
            event_type="auth.login_failed",
            source_module="identity",
            message="Login failed for observability test.",
            severity=SystemEventLog.Severity.WARNING,
        )
        self.assertEqual(SystemEventLog.objects.count(), 1)

    def test_error_incident_service_updates_occurrences(self):
        ErrorIncidentService.register_error_incident(
            incident_key="billing:invoice-error",
            source_module="billing",
            error_type="InvoiceError",
            message="Invoice generation failed.",
        )
        incident = ErrorIncidentService.register_error_incident(
            incident_key="billing:invoice-error",
            source_module="billing",
            error_type="InvoiceError",
            message="Invoice generation failed again.",
        )
        self.assertEqual(incident.occurrences_count, 2)
        self.assertEqual(ErrorIncident.objects.count(), 1)

    def test_metric_counter_service_increments_counter(self):
        counter = MetricCounterService.increment_metric(
            metric_key="auth.login_success_count",
            source_module="identity",
        )
        self.assertEqual(counter.value, 1)
        counter.refresh_from_db()
        self.assertEqual(MetricCounter.objects.count(), 1)

    def test_job_trace_service_registers_trace(self):
        trace = JobExecutionTraceService.start_job(
            job_name="integration.sync",
            source_module="integration_bus",
            payload={"task_id": 1},
        )
        JobExecutionTraceService.complete_job(trace=trace, payload={"task_id": 1, "status": "done"})
        trace.refresh_from_db()
        self.assertEqual(trace.status, JobExecutionTrace.Status.COMPLETED)
        self.assertIsNotNone(trace.completed_at)

    def test_platform_summary_returns_expected_blocks(self):
        response = self.client.get(reverse("observability-platform-summary"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("health", response.data)
        self.assertIn("recent_errors", response.data)
        self.assertIn("latest_audits", response.data)
        self.assertIn("recent_jobs", response.data)

    def test_audit_log_carries_company_and_request_context(self):
        company = Company.objects.create(name="Observability Tenant", slug="observability-tenant")
        AccessAuditService.log(
            user=self.user,
            action="reports_exported",
            domain="reports",
            resource_type="report",
            resource_id="RT-OS-001",
            decision="allow",
            company=company,
            request_id="req-audit-001",
            correlation_id="corr-audit-001",
            origin="test-suite",
            before_state={"status": "draft"},
            after_state={"status": "exported"},
        )

        audit = AccessAuditLog.objects.latest("created_at")
        self.assertEqual(audit.company, company)
        self.assertEqual(audit.request_id, "req-audit-001")
        self.assertEqual(audit.origin, "test-suite")
        self.assertEqual(audit.after_state["status"], "exported")
