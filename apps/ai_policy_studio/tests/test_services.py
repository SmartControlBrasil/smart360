from django.test import TestCase
from django.utils import timezone

from apps.ai_agents_center.models import AgentActionProposal, AgentDefinition, AgentExecutionPolicy, AgentRun
from apps.ai_decision_engine.models import AgentDecision
from apps.ai_decision_engine.services.orchestrator import DecisionOrchestrator
from apps.ai_policy_studio.models import Policy, PolicyRule, PolicyScope
from apps.ai_policy_studio.services.engine import PolicyStudioEngine
from apps.ai_policy_studio.services.versioning import PolicyVersioningService
from tests.factories.core import MembershipFactory
from tests.factories.smart_system import AssetFactory, OperationalSiteFactory


class PolicyStudioServiceTests(TestCase):
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

    def test_policy_engine_applies_tenant_specific_rule(self):
        policy = Policy.objects.create(
            slug="tenant-decision-deny-work-order",
            name="Tenant deny work order",
            tenant_scope="company",
            is_global=False,
            status=Policy.Status.ACTIVE,
        )
        PolicyScope.objects.create(policy=policy, company=self.company, module_slug="ai_decision_engine", action_type="create_work_order_proposal", priority=1)
        PolicyRule.objects.create(
            policy=policy,
            action_type="create_work_order_proposal",
            risk_level=PolicyRule.RiskLevel.HIGH,
            result=PolicyRule.EvaluationResult.DENY,
            allowed=False,
            rationale="Tenant blocks AI-created work orders.",
        )

        result = PolicyStudioEngine.evaluate(
            module_slug="ai_decision_engine",
            action_type="create_work_order_proposal",
            company=self.company,
            site=self.site,
            risk_level="high",
            autonomy_level=1,
            agent_slug=self.agent.slug,
        )

        self.assertEqual(result.result, PolicyRule.EvaluationResult.DENY)
        self.assertFalse(result.allowed)

    def test_decision_engine_is_blocked_when_policy_studio_denies(self):
        policy = Policy.objects.create(
            slug="tenant-decision-deny-investigation",
            name="Tenant deny investigation",
            tenant_scope="company",
            is_global=False,
            status=Policy.Status.ACTIVE,
        )
        PolicyScope.objects.create(policy=policy, company=self.company, module_slug="ai_decision_engine", action_type="create_investigation_task", priority=1)
        PolicyRule.objects.create(
            policy=policy,
            action_type="create_investigation_task",
            risk_level=PolicyRule.RiskLevel.LOW,
            result=PolicyRule.EvaluationResult.DENY,
            allowed=False,
            rationale="Tenant forbids this autonomous investigation path.",
        )
        proposal = AgentActionProposal.objects.create(
            agent_run=self.run,
            action_type="create_investigation_task",
            target_entity="asset",
            target_entity_id=str(self.asset.public_id),
            title="Investigation",
            summary="Test deny",
            proposed_payload={"asset_public_id": str(self.asset.public_id)},
            priority="low",
            approval_required=False,
        )

        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)

        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.AUTO_BLOCKED)
        self.assertIn("policy_studio", decision.explainability_payload)

    def test_tenant_isolation_keeps_other_company_rule_out(self):
        other_membership = MembershipFactory()
        other_policy = Policy.objects.create(
            slug="other-company-policy",
            name="Other company policy",
            tenant_scope="company",
            is_global=False,
            status=Policy.Status.ACTIVE,
        )
        PolicyScope.objects.create(policy=other_policy, company=other_membership.company, module_slug="ai_decision_engine", action_type="mark_asset_attention", priority=1)
        PolicyRule.objects.create(
            policy=other_policy,
            action_type="mark_asset_attention",
            risk_level=PolicyRule.RiskLevel.LOW,
            result=PolicyRule.EvaluationResult.DENY,
            allowed=False,
            rationale="Only for another company.",
        )

        result = PolicyStudioEngine.evaluate(
            module_slug="ai_decision_engine",
            action_type="mark_asset_attention",
            company=self.company,
            site=self.site,
            risk_level="low",
            autonomy_level=2,
        )

        self.assertNotEqual(getattr(result.policy, "slug", ""), "other-company-policy")

    def test_policy_versioning_creates_snapshots(self):
        policy = Policy.objects.create(
            slug="versioned-policy",
            name="Versioned policy",
            tenant_scope="global",
            is_global=True,
            status=Policy.Status.ACTIVE,
        )
        PolicyScope.objects.create(policy=policy, module_slug="ai_decision_engine", priority=10)
        PolicyRule.objects.create(policy=policy, action_type="", risk_level=PolicyRule.RiskLevel.ANY, result=PolicyRule.EvaluationResult.ALLOW, rationale="Initial.")

        first = PolicyVersioningService.create_version(policy=policy, created_by_user=self.user, change_summary="Initial snapshot")
        policy.description = "Updated"
        policy.save(update_fields=["description", "updated_at"])
        second = PolicyVersioningService.create_version(policy=policy, created_by_user=self.user, change_summary="Updated description")

        self.assertEqual(first, 1)
        self.assertEqual(second, 2)
        self.assertEqual(policy.versions.count(), 2)
