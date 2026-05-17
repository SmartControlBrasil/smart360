from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.access_control_center.models import (
    AccessPolicy,
    PermissionAction,
    PermissionDomain,
    PolicyAssignment,
    Role,
    RolePermission,
    SensitiveActionApproval,
    UserRoleAssignment,
)
from apps.companies.models import Company
from apps.users.models import User


class AccessControlCenterApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="admin@smart360.local", password="StrongPass123!", first_name="Admin")
        self.approver = User.objects.create_user(
            email="ops@smart360.local",
            password="StrongPass123!",
            first_name="Ops",
        )
        self.company = Company.objects.create(
            name="SMART360 Internal",
            legal_name="SMART360 Internal LTDA",
            slug="smart360-internal",
            status=Company.Status.ACTIVE,
        )
        self.domain = PermissionDomain.objects.create(name="Billing", module_name="billing")
        self.action = PermissionAction.objects.create(domain=self.domain, action_name="approve")
        self.role = Role.objects.create(name="Finance Admin", role_type=Role.RoleType.INTERNAL)
        RolePermission.objects.create(
            role=self.role,
            permission_domain=self.domain,
            permission_action=self.action,
            is_allowed=True,
        )
        UserRoleAssignment.objects.create(
            user=self.user,
            role=self.role,
            company=self.company,
            scope_type=UserRoleAssignment.ScopeType.COMPANY,
        )
        self.client.force_authenticate(self.user)

    def test_check_permission_allows_by_role_assignment(self):
        response = self.client.post(
            reverse("access-control-check-permission"),
            {
                "domain_slug": self.domain.slug,
                "action_slug": self.action.slug,
                "company": self.company.id,
                "module_name": "billing",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["allowed"])

    def test_my_permissions_lists_effective_permissions(self):
        response = self.client.get(reverse("access-control-my-permissions"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["effective_decision"], "allow")

    def test_policy_evaluation_works_with_context(self):
        policy = AccessPolicy.objects.create(
            name="Own company only",
            domain=self.domain,
            policy_type=AccessPolicy.PolicyType.COMPANY_BOUNDARY,
            rule_definition_json={
                "logic": "all",
                "conditions": [{"field": "company_id", "operator": "equals_company_id"}],
            },
        )
        PolicyAssignment.objects.create(policy=policy, role=self.role)
        response = self.client.post(
            reverse("access-control-policy-evaluation"),
            {"policy": policy.id, "company": self.company.id, "context": {"company_id": self.company.id}},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["allowed"])

    def test_sensitive_approval_can_be_approved(self):
        approval = SensitiveActionApproval.objects.create(
            action_name="cancel_invoice",
            domain=self.domain,
            requested_by=self.user,
        )
        self.client.force_authenticate(self.approver)
        response = self.client.post(
            reverse("access-control-sensitive-approval-approve", args=[approval.id]),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        approval.refresh_from_db()
        self.assertEqual(approval.status, SensitiveActionApproval.Status.APPROVED)

