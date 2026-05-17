from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.access_control_center.models import PermissionAction, PermissionDomain, RolePermission
from apps.ai_policy_studio.models import Policy
from tests.factories.access_control import AccessRoleFactory, UserRoleAssignmentFactory
from tests.factories.core import MembershipFactory


class PolicyStudioApiTests(APITestCase):
    def setUp(self):
        self.membership = MembershipFactory()
        self.company = self.membership.company
        self.user = self.membership.user
        self._grant_access(self.user)
        self.client.force_authenticate(self.user)

    def _grant_access(self, user, *, role_name="Company Admin"):
        domain, _ = PermissionDomain.objects.get_or_create(
            slug="ai_agents_admin",
            defaults={"name": "ai_agents_admin", "module_name": "ai_agents_center", "description": "AI admin"},
        )
        role = AccessRoleFactory(name=role_name)
        for action_name in ("view", "approve", "manage"):
            action, _ = PermissionAction.objects.get_or_create(domain=domain, action_name=action_name, defaults={"is_active": True})
            RolePermission.objects.get_or_create(role=role, permission_domain=domain, permission_action=action, defaults={"is_allowed": True})
        UserRoleAssignmentFactory(user=user, role=role, company=self.company)

    def test_policy_evaluate_endpoint_returns_result(self):
        response = self.client.post(
            reverse("ai-policy-studio-policy-evaluate"),
            {
                "module_slug": "ai_decision_engine",
                "action_type": "create_work_order_proposal",
                "company": self.company.id,
                "risk_level": "high",
                "autonomy_level": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("result", response.data)

    def test_policy_version_action_creates_new_version(self):
        policy = Policy.objects.create(
            slug="api-version-policy",
            name="API version policy",
            tenant_scope="global",
            is_global=True,
            status=Policy.Status.ACTIVE,
        )

        response = self.client.post(
            reverse("ai-policy-studio-policy-version", args=[policy.public_id]),
            {"change_summary": "manual version"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        policy.refresh_from_db()
        self.assertEqual(policy.version, 1)

    def test_policy_simulate_action_returns_summary(self):
        policy = Policy.objects.get(slug="global-decision-governance")

        response = self.client.post(
            reverse("ai-policy-studio-policy-simulate", args=[policy.public_id]),
            {"note": "simulate impact"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("result_payload", response.data)
