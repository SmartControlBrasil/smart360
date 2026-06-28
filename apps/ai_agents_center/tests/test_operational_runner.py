from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.ai_agents_center.models import AgentDefinition, AgentRun
from apps.companies.models import Company
from apps.smart_system.models import MaintenanceClient, OperationalSite


class OperationalAgentsRunnerCommandTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Piloto Operacional", slug="piloto-operacional")
        self.client_model = MaintenanceClient.objects.create(company=self.company, display_name="Piloto Operacional")
        self.site = OperationalSite.objects.create(maintenance_client=self.client_model, name="Unidade Piloto")

    def _create_run(self, *, agent_slug, site, trigger_reference):
        return AgentRun.objects.create(
            agent=AgentDefinition.objects.get(slug=agent_slug),
            company=site.maintenance_client.company,
            site=site,
            trigger_type=AgentRun.TriggerType.SCHEDULED,
            trigger_reference=trigger_reference,
            status=AgentRun.Status.COMPLETED,
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )

    @patch("apps.ai_agents_center.services.operational_runner.SchedulingAgentTriggerService.run_day_analysis")
    @patch("apps.ai_agents_center.services.operational_runner.MaintenanceAgentTriggerService.run_site_analysis")
    def test_run_operational_agents_executes_and_skips_completed_repeat(self, maintenance_mock, scheduling_mock):
        target_date = "2026-06-29"

        def maintenance_side_effect(*, site, trigger_type, trigger_reference):
            return self._create_run(agent_slug="maintenance-agent", site=site, trigger_reference=trigger_reference)

        def scheduling_side_effect(*, company, site, target_date, trigger_type, trigger_reference):
            return self._create_run(agent_slug="scheduling-agent", site=site, trigger_reference=trigger_reference)

        maintenance_mock.side_effect = maintenance_side_effect
        scheduling_mock.side_effect = scheduling_side_effect

        call_command("run_operational_agents", date=target_date, stdout=StringIO())

        self.assertEqual(maintenance_mock.call_count, 1)
        self.assertEqual(scheduling_mock.call_count, 1)
        self.assertEqual(AgentRun.objects.filter(status=AgentRun.Status.COMPLETED).count(), 2)

        maintenance_mock.reset_mock()
        scheduling_mock.reset_mock()
        output = StringIO()
        call_command("run_operational_agents", date=target_date, stdout=output)

        self.assertEqual(maintenance_mock.call_count, 0)
        self.assertEqual(scheduling_mock.call_count, 0)
        self.assertEqual(AgentRun.objects.filter(status=AgentRun.Status.COMPLETED).count(), 2)
        self.assertIn("SKIPPED maintenance-agent", output.getvalue())
        self.assertIn("SKIPPED scheduling-agent", output.getvalue())

    @patch("apps.ai_agents_center.services.operational_runner.SchedulingAgentTriggerService.run_day_analysis")
    @patch("apps.ai_agents_center.services.operational_runner.MaintenanceAgentTriggerService.run_site_analysis")
    def test_run_operational_agents_dry_run_only_plans(self, maintenance_mock, scheduling_mock):
        output = StringIO()

        call_command("run_operational_agents", dry_run=True, stdout=output)

        self.assertEqual(maintenance_mock.call_count, 0)
        self.assertEqual(scheduling_mock.call_count, 0)
        self.assertEqual(AgentRun.objects.count(), 0)
        self.assertIn("PLANNED maintenance-agent", output.getvalue())
        self.assertIn("PLANNED scheduling-agent", output.getvalue())
