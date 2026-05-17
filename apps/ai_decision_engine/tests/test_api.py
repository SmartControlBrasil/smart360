from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.access_control_center.models import PermissionAction, PermissionDomain, RolePermission
from apps.ai_agents_center.models import AgentActionProposal, AgentDefinition, AgentExecutionPolicy, AgentRun
from apps.ai_decision_engine.models import AgentDecision
from apps.ai_decision_engine.services.orchestrator import DecisionOrchestrator
from tests.factories.access_control import AccessRoleFactory, UserRoleAssignmentFactory
from tests.factories.core import MembershipFactory, UserFactory
from tests.factories.smart_system import AssetFactory, OperationalSiteFactory


class DecisionEngineApiTests(APITestCase):
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
        AgentExecutionPolicy.objects.create(agent=self.agent, require_human_approval=True)
        self.run = AgentRun.objects.create(
            agent=self.agent,
            company=self.company,
            site=self.site,
            triggered_by=self.user,
            trigger_type=AgentRun.TriggerType.MANUAL,
            status=AgentRun.Status.COMPLETED,
        )
        self._grant_access(self.user, role_name="Maintenance Manager")
        self.client.force_authenticate(self.user)

    def _grant_access(self, user, *, role_name):
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

    def _decision(self):
        proposal = AgentActionProposal.objects.create(
            agent_run=self.run,
            action_type="open_inspection_work_order",
            target_entity="asset",
            target_entity_id=str(self.asset.public_id),
            title="Open inspection work order",
            summary="Inspection required",
            proposed_payload={"asset_public_id": str(self.asset.public_id)},
            priority="high",
            approval_required=True,
        )
        return DecisionOrchestrator.receive_action_proposal(proposal=proposal)

    def test_pending_decisions_endpoint_lists_scoped_decisions(self):
        decision = self._decision()

        response = self.client.get(reverse("ai-decision-pending"), {"company": self.company.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["public_id"], str(decision.public_id))

    def test_approve_endpoint_executes_decision(self):
        decision = self._decision()

        response = self.client.post(reverse("ai-decision-approve", args=[decision.public_id]), {"comment": "approved"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        decision.refresh_from_db()
        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.EXECUTED)

    def test_policy_list_endpoint_returns_catalog(self):
        response = self.client.get(reverse("ai-decision-policy-list"), {"company": self.company.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(item["action_type"] == "mark_asset_attention" for item in response.data["results"]))
