from django.test import TestCase
from django.utils import timezone

from apps.ai_agents_center.models import AgentActionProposal, AgentAssetAttentionFlag, AgentDefinition, AgentExecutionPolicy, AgentRun
from apps.ai_autonomous_ops.models import AutonomousExecution, AutonomousIncident, AutonomousModeConfig
from apps.ai_autonomous_ops.services.orchestrator import AutonomousOperationsService
from apps.ai_decision_engine.models import AgentDecision
from apps.ai_decision_engine.services.orchestrator import DecisionOrchestrator
from apps.ai_simulation_engine.models import SimulationType
from apps.observability_center.models import SystemEventLog
from tests.factories.core import MembershipFactory
from tests.factories.smart_system import AssetFactory, OperationalSiteFactory, RoutePlanFactory


class AutonomousOperationsServiceTests(TestCase):
    def setUp(self):
        self.membership = MembershipFactory()
        self.company = self.membership.company
        self.user = self.membership.user
        self.site = OperationalSiteFactory(maintenance_client__company=self.company)
        self.asset = AssetFactory(operational_site=self.site)
        self.agent = AgentDefinition.objects.create(
            slug="maintenance-agent",
            name="Maintenance Agent",
            domain=AgentDefinition.Domain.MAINTENANCE,
            status=AgentDefinition.Status.ACTIVE,
            autonomy_level=AgentDefinition.AutonomyLevel.PROPOSE,
            enabled=True,
        )
        AgentExecutionPolicy.objects.create(agent=self.agent, require_human_approval=True, allowed_action_types=["*"])
        self.run = AgentRun.objects.create(
            agent=self.agent,
            company=self.company,
            site=self.site,
            triggered_by=self.user,
            trigger_type=AgentRun.TriggerType.MANUAL,
            status=AgentRun.Status.COMPLETED,
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )

    def _configure_autonomy(
        self,
        *,
        mode_level=2,
        max_risk_level="low",
        allowed_action_types=None,
        blocked_action_types=None,
        requires_simulation_for=None,
        kill_switch_enabled=False,
        confidence_threshold_overrides=None,
    ):
        return AutonomousModeConfig.objects.create(
            company=self.company,
            is_enabled=True,
            mode_level=mode_level,
            max_risk_level=max_risk_level,
            allowed_action_types=allowed_action_types or ["mark_asset_attention", "create_investigation_task", "reorder_route_proposal"],
            blocked_action_types=blocked_action_types or [],
            requires_simulation_for=requires_simulation_for or [],
            kill_switch_enabled=kill_switch_enabled,
            confidence_threshold_overrides=confidence_threshold_overrides or {},
            confidence_threshold_default="0.70",
            max_executions_per_hour=30,
            max_executions_per_day=200,
            max_failures_per_day=5,
            max_rollbacks_per_day=5,
        )

    def _proposal(self, *, action_type, payload=None, target_entity="asset", target_entity_id=None, priority="medium"):
        return AgentActionProposal.objects.create(
            agent_run=self.run,
            action_type=action_type,
            target_entity=target_entity,
            target_entity_id=target_entity_id or str(self.asset.public_id),
            title=f"Proposal {action_type}",
            summary=f"Summary for {action_type}",
            proposed_payload=payload or {"asset_public_id": str(self.asset.public_id)},
            priority=priority,
            approval_required=False,
        )

    def test_low_risk_action_is_autoexecuted_when_policy_allows(self):
        self._configure_autonomy()
        proposal = self._proposal(
            action_type="mark_asset_under_watch",
            payload={"asset_public_id": str(self.asset.public_id), "attention_score": 87},
        )

        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)

        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.EXECUTED)
        autonomous_execution = AutonomousExecution.objects.get(source_decision=decision)
        self.assertEqual(autonomous_execution.execution_status, AutonomousExecution.ExecutionStatus.SUCCEEDED)
        self.assertTrue(AgentAssetAttentionFlag.objects.filter(asset=self.asset, status=AgentAssetAttentionFlag.Status.ACTIVE).exists())
        self.assertTrue(SystemEventLog.objects.filter(event_type="autonomy.execution.succeeded").exists())

    def test_blocked_action_does_not_autoexecute_and_returns_to_approval(self):
        self._configure_autonomy(blocked_action_types=["mark_asset_attention"])
        proposal = self._proposal(
            action_type="mark_asset_under_watch",
            payload={"asset_public_id": str(self.asset.public_id), "attention_score": 75},
        )

        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)

        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.AWAITING_APPROVAL)
        autonomous_execution = AutonomousExecution.objects.get(source_decision=decision)
        self.assertEqual(autonomous_execution.execution_status, AutonomousExecution.ExecutionStatus.BLOCKED)
        self.assertIn("bloqueado", autonomous_execution.execution_summary.lower())

    def test_low_confidence_candidate_is_blocked(self):
        self._configure_autonomy(confidence_threshold_overrides={"mark_asset_attention": "0.95"})
        proposal = self._proposal(
            action_type="mark_asset_under_watch",
            payload={"asset_public_id": str(self.asset.public_id), "attention_score": 70},
        )

        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)

        autonomous_execution = AutonomousExecution.objects.get(source_decision=decision)
        self.assertEqual(autonomous_execution.execution_status, AutonomousExecution.ExecutionStatus.BLOCKED)
        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.AWAITING_APPROVAL)
        self.assertIn("confidence", autonomous_execution.execution_summary.lower())

    def test_required_simulation_blocks_execution_when_type_is_unavailable(self):
        self._configure_autonomy(mode_level=3, max_risk_level="medium", requires_simulation_for=["reorder_route_proposal"])
        SimulationType.objects.filter(slug="route_reorder_simulation").update(enabled=False)
        route_plan = RoutePlanFactory(company=self.company, operational_site=self.site, technician=self.user)
        proposal = self._proposal(
            action_type="reorder_route_plan",
            target_entity="route_plan",
            target_entity_id=str(route_plan.public_id),
            payload={"route_plan_public_id": str(route_plan.public_id), "technician_id": self.user.id},
            priority="medium",
        )
        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)
        decision.can_auto_execute = True
        decision.requires_human_approval = False
        decision.save(update_fields=["can_auto_execute", "requires_human_approval", "updated_at"])

        autonomous_execution = AutonomousOperationsService.evaluate_and_execute(decision=decision)

        self.assertEqual(autonomous_execution.execution_status, AutonomousExecution.ExecutionStatus.BLOCKED)
        self.assertIn("simulacao obrigatoria ausente", autonomous_execution.execution_summary.lower())

    def test_kill_switch_interrupts_new_autoexecutions(self):
        self._configure_autonomy(kill_switch_enabled=True)
        proposal = self._proposal(action_type="mark_asset_under_watch", payload={"asset_public_id": str(self.asset.public_id), "attention_score": 80})

        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)

        autonomous_execution = AutonomousExecution.objects.get(source_decision=decision)
        self.assertEqual(autonomous_execution.execution_status, AutonomousExecution.ExecutionStatus.BLOCKED)
        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.AWAITING_APPROVAL)

    def test_supported_rollback_reverts_execution_and_updates_status(self):
        self._configure_autonomy()
        proposal = self._proposal(
            action_type="mark_asset_under_watch",
            payload={"asset_public_id": str(self.asset.public_id), "attention_score": 92},
        )
        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)
        autonomous_execution = AutonomousExecution.objects.get(source_decision=decision)

        AutonomousOperationsService.rollback(autonomous_execution=autonomous_execution, requested_by=self.user)

        autonomous_execution.refresh_from_db()
        flag = AgentAssetAttentionFlag.objects.get(asset=self.asset)
        self.assertEqual(autonomous_execution.execution_status, AutonomousExecution.ExecutionStatus.ROLLED_BACK)
        self.assertEqual(autonomous_execution.rollback_status, AutonomousExecution.RollbackStatus.EXECUTED)
        self.assertEqual(flag.status, AgentAssetAttentionFlag.Status.RESOLVED)
        self.assertTrue(SystemEventLog.objects.filter(event_type="autonomy.rollback.succeeded").exists())

    def test_execution_failure_generates_autonomy_incident(self):
        self._configure_autonomy()
        empty_site = OperationalSiteFactory(maintenance_client__company=self.company)
        failing_run = AgentRun.objects.create(
            agent=self.agent,
            company=self.company,
            site=empty_site,
            triggered_by=self.user,
            trigger_type=AgentRun.TriggerType.MANUAL,
            status=AgentRun.Status.COMPLETED,
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )
        proposal = AgentActionProposal.objects.create(
            agent_run=failing_run,
            action_type="create_investigation_task",
            target_entity="site",
            target_entity_id=str(empty_site.public_id),
            title="Open investigation",
            summary="Should fail because site has no anchor asset",
            proposed_payload={},
            priority="low",
            approval_required=False,
        )

        with self.assertRaises(Exception):
            DecisionOrchestrator.receive_action_proposal(proposal=proposal)

        decision = AgentDecision.objects.get(agent_action_proposal=proposal)
        autonomous_execution = AutonomousExecution.objects.get(source_decision=decision)
        self.assertEqual(autonomous_execution.execution_status, AutonomousExecution.ExecutionStatus.FAILED)
        self.assertTrue(AutonomousIncident.objects.filter(autonomous_execution=autonomous_execution, incident_type="execution_failed").exists())
