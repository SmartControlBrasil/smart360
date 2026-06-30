from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from config.celery import app as celery_app

from apps.ai_agents_center.models import (
    AgentActionProposal,
    AgentAssetAttentionFlag,
    AgentDefinition,
    AgentRecommendation,
    AgentRun,
    AgentScheduleHealthFlag,
)
from apps.ai_agents_center.services.operational_runner import OperationalAgentRunItem
from apps.ai_agents_center.services.orchestrator import AgentCoordinatorService
from apps.ai_agents_center.services.registry import AgentRegistryService
from apps.ai_agents_center.tasks import run_daily_operational_agents
from apps.admin_shell.services.ai_agents_center import get_operations_health_context
from apps.ai_decision_engine.models import AgentDecision, DecisionExecution
from apps.companies.models import Company
from apps.smart_system.models import Asset, AssetCategory, FailureEvent, MaintenanceClient, OperationalSite, ScheduledVisit, ServiceOrder


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
        self.assertEqual(AgentRecommendation.objects.count(), 0)
        self.assertEqual(AgentActionProposal.objects.count(), 0)
        self.assertEqual(AgentAssetAttentionFlag.objects.count(), 0)
        self.assertEqual(AgentScheduleHealthFlag.objects.count(), 0)
        self.assertIn("PLANNED maintenance-agent", output.getvalue())
        self.assertIn("PLANNED scheduling-agent", output.getvalue())

    @patch("apps.ai_agents_center.services.operational_runner.SchedulingAgentTriggerService.run_day_analysis")
    @patch("apps.ai_agents_center.services.operational_runner.MaintenanceAgentTriggerService.run_site_analysis")
    def test_operational_pilot_smoke_validates_registry_dry_run_and_health_context(self, maintenance_mock, scheduling_mock):
        output = StringIO()

        call_command("run_operational_agents", dry_run=True, stdout=output)

        maintenance_agent = AgentRegistryService.get_agent_definition("maintenance-agent")
        scheduling_agent = AgentRegistryService.get_agent_definition("scheduling-agent")
        health_context = get_operations_health_context(tenant_context={"active_company": self.company})
        status_slugs = {item["agent_slug"] for item in health_context["operational_agent_status"]}

        self.assertEqual(maintenance_mock.call_count, 0)
        self.assertEqual(scheduling_mock.call_count, 0)
        self.assertEqual(AgentRun.objects.count(), 0)
        self.assertTrue(maintenance_agent.enabled)
        self.assertTrue(scheduling_agent.enabled)
        self.assertIn("PLANNED maintenance-agent", output.getvalue())
        self.assertIn("PLANNED scheduling-agent", output.getvalue())
        self.assertEqual(status_slugs, {"maintenance-agent", "scheduling-agent"})
        self.assertEqual(len(health_context["summary_cards"]), 4)
        self.assertIn("detected_risks", health_context)
        self.assertIn("recent_runs", health_context)


class OperationalAgentsCeleryTaskTests(TestCase):
    def test_run_daily_operational_agents_task_calls_runner(self):
        summary = {
            "run_date": timezone.localdate(),
            "target_date": timezone.localdate() + timedelta(days=1),
            "site_count": 1,
            "results": [
                OperationalAgentRunItem(
                    agent_slug="maintenance-agent",
                    site_id=10,
                    site_name="Unidade Piloto",
                    trigger_reference="operational:maintenance:daily_critical_assets:2026-06-28",
                    status="executed",
                    run_id=123,
                ),
                OperationalAgentRunItem(
                    agent_slug="scheduling-agent",
                    site_id=10,
                    site_name="Unidade Piloto",
                    trigger_reference="date:2026-06-29",
                    status="skipped",
                ),
            ],
            "executed": 1,
            "skipped": 1,
            "planned": 0,
            "failed": 0,
        }

        with patch("apps.ai_agents_center.tasks.OperationalAgentsRunner.run_daily", return_value=summary) as runner_mock:
            payload = run_daily_operational_agents()

        runner_mock.assert_called_once_with(dry_run=False, force=False)
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["run_date"], summary["run_date"].isoformat())
        self.assertEqual(payload["target_date"], summary["target_date"].isoformat())
        self.assertEqual(payload["results"][0]["agent_slug"], "maintenance-agent")
        self.assertEqual(payload["results"][1]["agent_slug"], "scheduling-agent")

    def test_run_daily_operational_agents_task_reports_unexpected_failure(self):
        with patch("apps.ai_agents_center.tasks.OperationalAgentsRunner.run_daily", side_effect=RuntimeError("boom")):
            payload = run_daily_operational_agents()

        self.assertEqual(payload, {"status": "failed", "error": "unexpected_exception"})

    def test_operational_agents_beat_schedule_is_registered(self):
        beat_entry = celery_app.conf.beat_schedule["ai-agents-operational-daily-0630"]

        self.assertEqual(beat_entry["task"], "ai_agents_center.run_daily_operational_agents")
        self.assertEqual(str(beat_entry["schedule"]._orig_hour), "6")
        self.assertEqual(str(beat_entry["schedule"]._orig_minute), "30")


class OperationalProposalApprovalTests(TestCase):
    def setUp(self):
        AgentRegistryService.bootstrap_registry()
        self.user = get_user_model().objects.create_superuser(
            email="ops-approver@smart360.local",
            password="StrongPass123",
        )
        self.company = Company.objects.create(name="Aprovação Operacional", slug="aprovacao-operacional")
        self.client_model = MaintenanceClient.objects.create(company=self.company, display_name="Aprovação Operacional")
        self.site = OperationalSite.objects.create(maintenance_client=self.client_model, name="Unidade Aprovação")
        self.category = AssetCategory.objects.create(name="Categoria Aprovação", slug="categoria-aprovacao")
        self.asset = Asset.objects.create(
            operational_site=self.site,
            category=self.category,
            asset_tag="APP-001",
            name="Compressor Aprovação",
        )
        self.run = AgentRun.objects.create(
            agent=AgentDefinition.objects.get(slug="maintenance-agent"),
            company=self.company,
            site=self.site,
            trigger_type=AgentRun.TriggerType.SCHEDULED,
            trigger_reference="operational:test",
            status=AgentRun.Status.COMPLETED,
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )

    def _proposal(self, *, action_type="open_inspection_work_order"):
        return AgentActionProposal.objects.create(
            agent_run=self.run,
            action_type=action_type,
            target_entity="asset",
            target_entity_id=str(self.asset.public_id),
            title="Abrir inspeção operacional",
            summary="Inspeção aprovada pela fila operacional.",
            proposed_payload={"asset_public_id": str(self.asset.public_id), "maintenance_type": ServiceOrder.MaintenanceType.INSPECTION},
            priority="high",
            approval_required=True,
        )

    def test_operational_proposal_approval_executes_valid_decision_handler(self):
        proposal = self._proposal()
        existing_orders = ServiceOrder.objects.count()

        AgentCoordinatorService.approve_proposal(proposal=proposal, approved_by=self.user, company=self.company)

        proposal.refresh_from_db()
        decision = proposal.decision
        self.assertEqual(proposal.status, AgentActionProposal.Status.APPROVED)
        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.EXECUTED)
        self.assertEqual(ServiceOrder.objects.count(), existing_orders + 1)
        self.assertTrue(decision.executions.filter(execution_status=DecisionExecution.ExecutionStatus.SUCCEEDED).exists())

    def test_operational_proposal_without_handler_is_approved_without_breaking_queue(self):
        proposal = self._proposal()
        existing_orders = ServiceOrder.objects.count()

        with patch("apps.ai_decision_engine.services.handlers.DecisionHandlerRegistry.get_handler", return_value=None):
            AgentCoordinatorService.approve_proposal(proposal=proposal, approved_by=self.user, company=self.company)

        proposal.refresh_from_db()
        decision = proposal.decision
        self.assertEqual(proposal.status, AgentActionProposal.Status.APPROVED)
        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.APPROVED)
        self.assertIn("no handler registered", decision.decision_reason)
        self.assertEqual(ServiceOrder.objects.count(), existing_orders)
        self.assertFalse(decision.executions.exists())


class OperationalPilotSeedCommandTests(TestCase):
    def test_seed_operational_pilot_data_creates_minimum_dataset(self):
        output = StringIO()

        call_command("seed_operational_pilot_data", stdout=output)

        company = Company.objects.get(slug="empresa-piloto-smart360")
        site = OperationalSite.objects.get(maintenance_client__company=company, name="Unidade Piloto Operacional")
        self.assertEqual(Asset.objects.filter(operational_site=site).count(), 5)
        self.assertGreaterEqual(Asset.objects.filter(operational_site=site, criticality=Asset.Criticality.CRITICAL).count(), 1)
        self.assertEqual(ServiceOrder.objects.filter(operational_site=site, order_number__startswith="OPS-PILOT-OS-").count(), 8)
        self.assertEqual(FailureEvent.objects.filter(asset__operational_site=site).count(), 4)
        self.assertEqual(ScheduledVisit.objects.filter(company=company, operational_site=site).count(), 5)
        self.assertIn("Seed operacional do piloto concluído", output.getvalue())
        self.assertIn("assets=5", output.getvalue())
        self.assertIn("visits=5", output.getvalue())

    def test_seed_operational_pilot_data_is_idempotent(self):
        call_command("seed_operational_pilot_data", stdout=StringIO())
        first_counts = {
            "companies": Company.objects.filter(slug="empresa-piloto-smart360").count(),
            "sites": OperationalSite.objects.filter(code="OPS-PILOT-001").count(),
            "assets": Asset.objects.filter(asset_tag__startswith="OPS-PILOT-").count(),
            "orders": ServiceOrder.objects.filter(order_number__startswith="OPS-PILOT-OS-").count(),
            "failures": FailureEvent.objects.filter(asset__asset_tag__startswith="OPS-PILOT-").count(),
            "visits": ScheduledVisit.objects.filter(metadata__seed_key="operational_pilot").count(),
        }

        call_command("seed_operational_pilot_data", stdout=StringIO())
        second_counts = {
            "companies": Company.objects.filter(slug="empresa-piloto-smart360").count(),
            "sites": OperationalSite.objects.filter(code="OPS-PILOT-001").count(),
            "assets": Asset.objects.filter(asset_tag__startswith="OPS-PILOT-").count(),
            "orders": ServiceOrder.objects.filter(order_number__startswith="OPS-PILOT-OS-").count(),
            "failures": FailureEvent.objects.filter(asset__asset_tag__startswith="OPS-PILOT-").count(),
            "visits": ScheduledVisit.objects.filter(metadata__seed_key="operational_pilot").count(),
        }

        self.assertEqual(second_counts, first_counts)

    @patch("apps.ai_agents_center.services.operational_runner.SchedulingAgentTriggerService.run_day_analysis")
    @patch("apps.ai_agents_center.services.operational_runner.MaintenanceAgentTriggerService.run_site_analysis")
    def test_run_operational_agents_dry_run_after_seed(self, maintenance_mock, scheduling_mock):
        call_command("seed_operational_pilot_data", stdout=StringIO())
        output = StringIO()

        call_command("run_operational_agents", dry_run=True, stdout=output)

        self.assertEqual(maintenance_mock.call_count, 0)
        self.assertEqual(scheduling_mock.call_count, 0)
        self.assertIn("PLANNED maintenance-agent", output.getvalue())
        self.assertIn("PLANNED scheduling-agent", output.getvalue())

    def test_run_operational_agents_real_execution_after_seed_creates_expected_data(self):
        call_command("seed_operational_pilot_data", stdout=StringIO())
        target_date = (timezone.localdate() + timedelta(days=1)).isoformat()

        call_command("run_operational_agents", date=target_date, stdout=StringIO())

        self.assertEqual(AgentRun.objects.filter(status=AgentRun.Status.COMPLETED).count(), 2)
        self.assertTrue(AgentRecommendation.objects.filter(agent_run__agent__slug="maintenance-agent").exists())
        self.assertTrue(AgentRecommendation.objects.filter(agent_run__agent__slug="scheduling-agent").exists())
        self.assertTrue(AgentActionProposal.objects.filter(agent_run__agent__slug__in=["maintenance-agent", "scheduling-agent"]).exists())
        self.assertTrue(
            AgentAssetAttentionFlag.objects.filter(agent__slug="maintenance-agent").exists()
            or AgentScheduleHealthFlag.objects.filter(agent__slug="scheduling-agent").exists()
        )

    def test_seed_operational_pilot_data_reset_removes_only_seed_records(self):
        other_company = Company.objects.create(name="Cliente Real", slug="cliente-real")
        call_command("seed_operational_pilot_data", stdout=StringIO())

        call_command("seed_operational_pilot_data", reset=True, stdout=StringIO())

        self.assertTrue(Company.objects.filter(pk=other_company.pk).exists())
        self.assertFalse(Company.objects.filter(slug="empresa-piloto-smart360").exists())
        self.assertFalse(Asset.objects.filter(asset_tag__startswith="OPS-PILOT-").exists())
        self.assertFalse(ServiceOrder.objects.filter(order_number__startswith="OPS-PILOT-OS-").exists())



class OperationalAgentsRuntimeCheckCommandTests(TestCase):
    def setUp(self):
        AgentRegistryService.bootstrap_registry()
        self.company = Company.objects.create(name="Diagnostico Operacional", slug="diagnostico-operacional")
        self.client_model = MaintenanceClient.objects.create(company=self.company, display_name="Diagnostico Operacional")
        self.site = OperationalSite.objects.create(maintenance_client=self.client_model, name="Unidade Diagnostico")
        self.category = AssetCategory.objects.create(name="Categoria Diagnostico", slug="categoria-diagnostico")
        self.asset = Asset.objects.create(
            operational_site=self.site,
            category=self.category,
            asset_tag="DIAG-001",
            name="Ativo Diagnostico",
        )

    def _run_command(self):
        output = StringIO()
        before_counts = {
            "agent_runs": AgentRun.objects.count(),
            "action_proposals": AgentActionProposal.objects.count(),
        }

        call_command("check_operational_agents_runtime", stdout=output)

        after_counts = {
            "agent_runs": AgentRun.objects.count(),
            "action_proposals": AgentActionProposal.objects.count(),
        }
        self.assertEqual(after_counts, before_counts)
        return output.getvalue()

    def test_check_operational_agents_runtime_command_runs_without_persisting_and_handles_no_runs(self):
        output = self._run_command()

        self.assertIn("registry maintenance-agent code=present db=present", output)
        self.assertIn("registry scheduling-agent code=present db=present", output)
        self.assertIn("task ai_agents_center.run_daily_operational_agents import=present celery=registered", output)
        self.assertIn("beat ai-agents-operational-daily-0630 task=ok schedule=present time=06:30", output)
        self.assertIn("timezone django=America/Sao_Paulo celery=America/Sao_Paulo match=yes", output)
        self.assertIn("agent_runs none_found", output)
        self.assertIn("pending_proposals older_than_24h=0", output)

    def test_check_operational_agents_runtime_command_reports_old_pending_proposals(self):
        agent_run = AgentRun.objects.create(
            agent=AgentDefinition.objects.get(slug="maintenance-agent"),
            company=self.company,
            site=self.site,
            trigger_type=AgentRun.TriggerType.SCHEDULED,
            trigger_reference="diagnostic",
            status=AgentRun.Status.COMPLETED,
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )
        proposal = AgentActionProposal.objects.create(
            agent_run=agent_run,
            action_type="open_inspection_work_order",
            target_entity="asset",
            target_entity_id=str(self.asset.public_id),
            title="Proposta diagnostica",
            summary="Proposta usada para validar o comando de runtime.",
            proposed_payload={"asset_public_id": str(self.asset.public_id)},
            priority="medium",
            approval_required=True,
        )
        AgentActionProposal.objects.filter(pk=proposal.pk).update(created_at=timezone.now() - timedelta(days=2))

        output = self._run_command()

        self.assertIn("agent_runs latest=maintenance-agent", output)
        self.assertIn("pending_proposals older_than_24h=1", output)
