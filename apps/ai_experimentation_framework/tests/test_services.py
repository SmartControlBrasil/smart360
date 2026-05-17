from django.test import TestCase
from django.utils import timezone

from apps.ai_agents_center.models import AgentActionProposal, AgentDefinition, AgentExecutionPolicy, AgentRun
from apps.ai_decision_engine.services.orchestrator import DecisionOrchestrator
from apps.ai_experimentation_framework.models import Experiment, ExperimentAssignment, ExperimentMetric
from apps.ai_experimentation_framework.services.analysis import ExperimentAnalysisService
from apps.ai_experimentation_framework.services.engine import ExperimentationEngine
from apps.ai_optimization_loop.models import OptimizationProposal
from apps.observability_center.models import SystemEventLog
from tests.factories.core import MembershipFactory
from tests.factories.smart_system import AssetFactory, OperationalSiteFactory


class ExperimentationFrameworkServiceTests(TestCase):
    def setUp(self):
        self.membership = MembershipFactory()
        self.company = self.membership.company
        self.user = self.membership.user
        self.site = OperationalSiteFactory(maintenance_client__company=self.company)
        self.asset = AssetFactory(operational_site=self.site)
        self.agent = AgentDefinition.objects.create(
            slug="experimentation-agent",
            name="Experimentation Agent",
            domain=AgentDefinition.Domain.MAINTENANCE,
            status=AgentDefinition.Status.ACTIVE,
            autonomy_level=AgentDefinition.AutonomyLevel.PROPOSE,
            enabled=True,
        )
        AgentExecutionPolicy.objects.create(agent=self.agent, require_human_approval=True, allowed_action_types=["*"])
        self.agent_run = AgentRun.objects.create(
            agent=self.agent,
            company=self.company,
            site=self.site,
            triggered_by=self.user,
            trigger_type=AgentRun.TriggerType.MANUAL,
            status=AgentRun.Status.COMPLETED,
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )

    def test_assignment_is_consistent_for_same_entity(self):
        experiment = ExperimentationEngine.create_experiment(
            name="Matching strategy test",
            description="A/B for matching",
            target_component=Experiment.TargetComponent.AGENT,
            target_reference="maintenance-agent",
            company=self.company,
            site=self.site,
            created_by_user=self.user,
            variants=[
                {"name": "Control", "slug": "control", "weight": 50, "is_control": True, "config_payload": {"strategy": "a"}},
                {"name": "Variant B", "slug": "variant-b", "weight": 50, "config_payload": {"strategy": "b"}},
            ],
        )

        first = ExperimentationEngine.resolve_assignment(
            target_component=Experiment.TargetComponent.AGENT,
            target_reference="maintenance-agent",
            entity_key="company:1:agent:maintenance-agent",
            entity_type="agent_run",
            company=self.company,
            site=self.site,
            context={"agent_slug": "maintenance-agent"},
        )
        second = ExperimentationEngine.resolve_assignment(
            target_component=Experiment.TargetComponent.AGENT,
            target_reference="maintenance-agent",
            entity_key="company:1:agent:maintenance-agent",
            entity_type="agent_run",
            company=self.company,
            site=self.site,
            context={"agent_slug": "maintenance-agent"},
        )

        self.assertEqual(first.public_id, second.public_id)
        self.assertEqual(ExperimentAssignment.objects.filter(experiment=experiment).count(), 1)

    def test_analysis_picks_winner_and_persists_result(self):
        experiment = ExperimentationEngine.create_experiment(
            name="Routing heuristic test",
            description="A/B for routing",
            target_component=Experiment.TargetComponent.SIMULATION_ENGINE,
            target_reference="route_reorder_simulation",
            company=self.company,
            site=self.site,
            created_by_user=self.user,
            variants=[
                {"name": "Control", "slug": "control", "weight": 50, "is_control": True, "config_payload": {"heuristic": "baseline"}},
                {"name": "Variant B", "slug": "variant-b", "weight": 50, "config_payload": {"heuristic": "improved"}},
            ],
            min_sample_size=2,
            primary_metric="sla_gain",
        )
        control = experiment.variants.get(slug="control")
        variant_b = experiment.variants.get(slug="variant-b")
        for value in ("2.00", "3.00"):
            ExperimentMetric.objects.create(experiment=experiment, variant=control, metric_type="sla_gain", value=value)
        for value in ("6.00", "7.00"):
            ExperimentMetric.objects.create(experiment=experiment, variant=variant_b, metric_type="sla_gain", value=value)

        completed = ExperimentationEngine.complete_experiment(experiment=experiment, actor_user=self.user)

        completed.refresh_from_db()
        self.assertEqual(completed.status, Experiment.Status.COMPLETED)
        self.assertEqual(completed.winner_variant.slug, "variant-b")
        self.assertEqual(completed.result.primary_metric, "sla_gain")
        self.assertTrue(SystemEventLog.objects.filter(event_type="experiment.completed").exists())

    def test_promoting_variant_generates_optimization_proposal(self):
        experiment = ExperimentationEngine.create_experiment(
            name="Decision strictness test",
            description="A/B for decision policy",
            target_component=Experiment.TargetComponent.DECISION_ENGINE,
            target_reference="mark_asset_attention",
            company=self.company,
            site=self.site,
            created_by_user=self.user,
            variants=[
                {"name": "Control", "slug": "control", "weight": 50, "is_control": True, "config_payload": {"approval": False}},
                {"name": "Strict", "slug": "strict", "weight": 50, "config_payload": {"approval": True}},
            ],
            min_sample_size=1,
        )
        winner = experiment.variants.get(slug="strict")
        ExperimentationEngine.promote_variant(experiment=experiment, variant=winner, actor_user=self.user)

        experiment.refresh_from_db()
        self.assertEqual(experiment.status, Experiment.Status.PROMOTED)
        self.assertEqual(experiment.winner_variant, winner)
        self.assertTrue(
            OptimizationProposal.objects.filter(source_outcome_type="experiment_result", source_outcome_reference=str(experiment.public_id)).exists()
        )

    def test_decision_runtime_attaches_experiment_assignment(self):
        ExperimentationEngine.create_experiment(
            name="Decision experiment",
            description="Decision engine variant test",
            target_component=Experiment.TargetComponent.DECISION_ENGINE,
            target_reference="mark_asset_attention",
            company=self.company,
            site=self.site,
            created_by_user=self.user,
            variants=[
                {"name": "Control", "slug": "control", "weight": 50, "is_control": True, "config_payload": {"policy_mode": "recommend"}},
                {"name": "Fast", "slug": "fast", "weight": 50, "config_payload": {"policy_mode": "auto"}},
            ],
        )
        proposal = AgentActionProposal.objects.create(
            agent_run=self.agent_run,
            action_type="mark_asset_under_watch",
            target_entity="asset",
            target_entity_id=str(self.asset.public_id),
            title="Mark asset under watch",
            summary="Runtime experiment test",
            proposed_payload={"asset_public_id": str(self.asset.public_id)},
            priority="low",
            approval_required=False,
        )

        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)

        self.assertIn("experiment", decision.explainability_payload)
        self.assertTrue(decision.explainability_payload["experiment"]["variant_slug"])

