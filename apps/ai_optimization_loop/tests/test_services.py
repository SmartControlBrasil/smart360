from django.test import TestCase
from django.utils import timezone

from apps.access_control_center.models import PermissionAction, PermissionDomain, RolePermission
from apps.ai_agents_center.models import AgentActionProposal, AgentDefinition, AgentExecutionPolicy, AgentRecommendation, AgentRun, ManagerCopilotConfiguration
from apps.ai_decision_engine.models import AgentDecision
from apps.ai_decision_engine.services.orchestrator import DecisionOrchestrator
from apps.ai_optimization_loop.models import DecisionOutcome, FeedbackSignal, OptimizationPolicy, OptimizationProposal, RecommendationOutcome, SimulationOutcome
from apps.ai_optimization_loop.services.approvals import OptimizationApprovalService
from apps.ai_optimization_loop.services.orchestrator import LearningOrchestrator
from apps.observability_center.models import SystemEventLog
from tests.factories.access_control import AccessRoleFactory, UserRoleAssignmentFactory
from tests.factories.core import MembershipFactory, UserFactory
from tests.factories.smart_system import AssetFactory, OperationalSiteFactory


class OptimizationLoopServiceTests(TestCase):
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
        AgentExecutionPolicy.objects.create(agent=self.agent, require_human_approval=True, allowed_action_types=["*"], max_recommendations=10)
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
        self._grant_access(self.user)

    def _grant_access(self, user, *, role_name="Company Admin"):
        domain, _ = PermissionDomain.objects.get_or_create(
            slug="ai_agents_admin",
            defaults={"name": "ai_agents_admin", "description": "AI admin", "module_name": "ai_agents_center", "is_active": True},
        )
        role = AccessRoleFactory(name=role_name)
        for action_name in ("view", "approve", "manage"):
            action, _ = PermissionAction.objects.get_or_create(domain=domain, action_name=action_name, defaults={"is_active": True})
            RolePermission.objects.get_or_create(
                role=role,
                permission_domain=domain,
                permission_action=action,
                defaults={"is_allowed": True},
            )
        UserRoleAssignmentFactory(user=user, role=role, company=self.company)
        return role

    def test_recommendation_feedback_creates_outcome(self):
        recommendation = AgentRecommendation.objects.create(
            agent_run=self.run,
            company=self.company,
            site=self.site,
            recommendation_type=AgentRecommendation.RecommendationType.INSIGHT,
            title="Review risk",
            summary="Recommendation summary",
            suggested_action="Open review task",
            status=AgentRecommendation.Status.ACCEPTED,
            entity_type="asset",
            entity_id=str(self.asset.public_id),
        )

        feedback = LearningOrchestrator.register_feedback(
            source_type=FeedbackSignal.SourceType.RECOMMENDATION,
            source_reference=recommendation.public_id,
            signal_type=FeedbackSignal.SignalType.USEFULNESS,
            score="92.00",
            company=self.company,
            site=self.site,
            user=self.user,
            comment="Useful recommendation",
        )

        self.assertEqual(feedback.signal_type, FeedbackSignal.SignalType.USEFULNESS)
        outcome = RecommendationOutcome.objects.get(recommendation=recommendation)
        self.assertEqual(outcome.outcome_status, RecommendationOutcome.OutcomeStatus.OBSERVED)
        self.assertGreater(outcome.effectiveness_score, 70)

    def test_decision_execution_persists_outcome_and_simulation_outcome(self):
        proposal = AgentActionProposal.objects.create(
            agent_run=self.run,
            action_type="mark_asset_under_watch",
            target_entity="asset",
            target_entity_id=str(self.asset.public_id),
            title="Mark asset under watch",
            summary="Auto materialize attention",
            proposed_payload={"asset_public_id": str(self.asset.public_id), "attention_score": 80},
            priority="medium",
            approval_required=False,
        )

        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)

        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.EXECUTED)
        outcome = DecisionOutcome.objects.get(decision=decision)
        self.assertEqual(outcome.result_status, DecisionOutcome.ResultStatus.SUCCEEDED)
        self.assertTrue(SimulationOutcome.objects.filter(simulation_run__decision=decision).exists())
        self.assertTrue(SystemEventLog.objects.filter(event_type="optimization.effectiveness.scored").exists())

    def test_failed_auto_decision_generates_optimization_proposal(self):
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
        outcome = DecisionOutcome.objects.get(decision=decision)
        self.assertEqual(outcome.result_status, DecisionOutcome.ResultStatus.FAILED)
        generated = OptimizationProposal.objects.filter(
            source_outcome_type="decision_outcome",
            source_outcome_reference=str(outcome.public_id),
        ).first()
        self.assertIsNotNone(generated)
        self.assertEqual(generated.proposal_type, "approval_requirement_adjustment")

    def test_policy_prevents_unauthorized_optimization_approval(self):
        recommendation = AgentRecommendation.objects.create(
            agent_run=self.run,
            company=self.company,
            site=self.site,
            recommendation_type=AgentRecommendation.RecommendationType.INSIGHT,
            title="Low quality recommendation",
            summary="summary",
            suggested_action="none",
            status=AgentRecommendation.Status.DISMISSED,
        )
        LearningOrchestrator.measure_recommendation(recommendation=recommendation)
        execution_policy = AgentExecutionPolicy.objects.get(agent=self.agent)
        proposal = LearningOrchestrator.generate_company_proposals(company=self.company)[0]
        outsider = UserFactory()

        with self.assertRaises(PermissionError):
            OptimizationApprovalService.approve(proposal=proposal, approved_by=outsider, comment="no access", apply=True)

        execution_policy.refresh_from_db()
        self.assertEqual(execution_policy.max_recommendations, 10)

    def test_approved_optimization_proposal_is_applied(self):
        execution_policy = AgentExecutionPolicy.objects.get(agent=self.agent)
        proposal = LearningOrchestrator.generate_company_proposals(company=self.company)
        if not proposal:
            proposal = [OptimizationProposal.objects.create(
                company=self.company,
                site=self.site,
                target_type="agent_execution_policy",
                target_reference=str(self.agent.public_id),
                proposal_type="ranking_adjustment",
                current_value={"max_recommendations": 10},
                proposed_value={"max_recommendations": 6},
                rationale="Reduce volume",
                evidence_summary="Low precision",
                expected_impact_summary="Improve precision",
                risk_level="medium",
                policy_applied=OptimizationPolicy.objects.get(slug="optimization-agent-execution-policy-ranking"),
            )]

        approved = OptimizationApprovalService.approve(proposal=proposal[0], approved_by=self.user, comment="apply now", apply=True)

        execution_policy.refresh_from_db()
        self.assertEqual(approved.status, OptimizationProposal.Status.APPLIED)
        self.assertEqual(execution_policy.max_recommendations, 6)

    def test_copilot_configuration_adjustment_can_be_applied(self):
        configuration = ManagerCopilotConfiguration.objects.create(company=self.company, is_enabled=True, behavior_config={"prompt_style": "brief"})
        policy = OptimizationPolicy.objects.get(slug="optimization-copilot-behavior-adjustment")
        proposal = OptimizationProposal.objects.create(
            company=self.company,
            target_type="copilot_configuration",
            target_reference=str(configuration.public_id),
            proposal_type="ranking_adjustment",
            current_value={"behavior_config": configuration.behavior_config},
            proposed_value={"behavior_config": {"prompt_style": "assertive", "show_quality_cards": True}},
            rationale="Improve executive guidance",
            evidence_summary="Repeated requests for clearer actionability",
            expected_impact_summary="More useful manager copilot responses",
            risk_level="low",
            policy_applied=policy,
        )

        OptimizationApprovalService.approve(proposal=proposal, approved_by=self.user, comment="ok", apply=True)

        configuration.refresh_from_db()
        self.assertEqual(configuration.behavior_config["prompt_style"], "assertive")
        self.assertTrue(configuration.behavior_config["show_quality_cards"])
