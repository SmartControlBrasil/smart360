from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.access_control_center.models import PermissionAction, PermissionDomain, RolePermission
from apps.ai_agents_center.models import AgentDefinition, AgentExecutionPolicy, AgentRun
from apps.ai_optimization_loop.models import FeedbackSignal, OptimizationPolicy, OptimizationProposal
from apps.ai_optimization_loop.services.orchestrator import LearningOrchestrator
from tests.factories.access_control import AccessRoleFactory, UserRoleAssignmentFactory
from tests.factories.core import MembershipFactory


class OptimizationLoopApiTests(APITestCase):
    def setUp(self):
        self.membership = MembershipFactory()
        self.company = self.membership.company
        self.user = self.membership.user
        self._grant_access(self.user)
        self.client.force_authenticate(self.user)
        self.agent = AgentDefinition.objects.create(
            slug="quality-agent",
            name="Quality Agent",
            domain=AgentDefinition.Domain.MAINTENANCE,
            status=AgentDefinition.Status.ACTIVE,
            autonomy_level=AgentDefinition.AutonomyLevel.PROPOSE,
            enabled=True,
        )
        AgentExecutionPolicy.objects.create(agent=self.agent, max_recommendations=9)
        self.run = AgentRun.objects.create(
            agent=self.agent,
            company=self.company,
            triggered_by=self.user,
            trigger_type=AgentRun.TriggerType.MANUAL,
            status=AgentRun.Status.COMPLETED,
        )

    def _grant_access(self, user, *, role_name="Company Admin"):
        domain, _ = PermissionDomain.objects.get_or_create(
            slug="ai_agents_admin",
            defaults={"name": "ai_agents_admin", "module_name": "ai_agents_center", "description": "AI admin"},
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

    def test_feedback_endpoint_registers_signal(self):
        response = self.client.post(
            reverse("ai-optimization-feedback-list"),
            {
                "source_type": "agent",
                "source_reference": self.agent.slug,
                "company": self.company.id,
                "signal_type": "quality",
                "score": "88.00",
                "comment": "Agent produced solid outputs",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FeedbackSignal.objects.count(), 1)

    def test_approve_proposal_endpoint_applies_adjustment(self):
        policy = OptimizationPolicy.objects.get(slug="optimization-agent-execution-policy-ranking")
        proposal = OptimizationProposal.objects.create(
            company=self.company,
            target_type="agent_execution_policy",
            target_reference=str(self.agent.public_id),
            proposal_type="ranking_adjustment",
            current_value={"max_recommendations": 9},
            proposed_value={"max_recommendations": 5},
            rationale="Reduce noise",
            evidence_summary="Low precision",
            expected_impact_summary="Improve precision",
            risk_level="medium",
            policy_applied=policy,
        )

        response = self.client.post(
            reverse("ai-optimization-proposal-approve", args=[proposal.public_id]),
            {"comment": "approved", "apply": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        AgentExecutionPolicy.objects.get(agent=self.agent).refresh_from_db()
        self.assertEqual(AgentExecutionPolicy.objects.get(agent=self.agent).max_recommendations, 5)

    def test_quality_endpoint_returns_agent_rows(self):
        response = self.client.get(reverse("ai-optimization-agent-quality"), {"company": self.company.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    def test_generate_endpoint_creates_batch_proposals(self):
        LearningOrchestrator.generate_company_proposals(company=self.company)

        response = self.client.post(
            reverse("ai-optimization-proposal-generate"),
            {"company": self.company.id},
            format="json",
        )

        self.assertIn(response.status_code, {status.HTTP_201_CREATED, status.HTTP_200_OK})
