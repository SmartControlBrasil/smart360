from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.access_control_center.models import PermissionAction, PermissionDomain, RolePermission
from apps.ai_experimentation_framework.models import Experiment
from tests.factories.access_control import AccessRoleFactory, UserRoleAssignmentFactory
from tests.factories.core import MembershipFactory
from tests.factories.smart_system import OperationalSiteFactory


class ExperimentationFrameworkApiTests(APITestCase):
    def setUp(self):
        self.membership = MembershipFactory()
        self.company = self.membership.company
        self.user = self.membership.user
        self.site = OperationalSiteFactory(maintenance_client__company=self.company)
        self._grant_access(self.user, role_name="AI Governance")
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

    def test_create_assign_record_metric_and_complete_experiment(self):
        create_response = self.client.post(
            reverse("ai-experiment-list"),
            {
                "name": "Copilot phrasing experiment",
                "description": "A/B de resposta do copilot",
                "target_component": "copilot",
                "target_reference": "manager-copilot",
                "company": self.company.id,
                "site": self.site.id,
                "primary_metric": "usefulness_score",
                "min_sample_size": 1,
                "variants": [
                    {"name": "Control", "slug": "control", "weight": 50, "is_control": True, "config_payload": {"tone": "standard"}},
                    {"name": "Variant B", "slug": "variant-b", "weight": 50, "config_payload": {"tone": "concise"}},
                ],
            },
            format="json",
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        experiment_public_id = create_response.data["public_id"]

        assign_response = self.client.post(
            reverse("ai-experiment-assign", args=[experiment_public_id]),
            {"entity_key": "session:123", "entity_type": "copilot_session", "context": {"channel": "manager"}},
            format="json",
        )
        self.assertEqual(assign_response.status_code, status.HTTP_200_OK)
        assignment_public_id = assign_response.data["public_id"]

        metric_response = self.client.post(
            reverse("ai-experiment-record-metric", args=[experiment_public_id]),
            {
                "assignment_public_id": assignment_public_id,
                "metric_type": "usefulness_score",
                "value": "8.50",
                "unit": "score",
                "source_component": "manager_copilot",
                "source_reference": "message-1",
            },
            format="json",
        )
        self.assertEqual(metric_response.status_code, status.HTTP_201_CREATED)

        complete_response = self.client.post(reverse("ai-experiment-complete", args=[experiment_public_id]), {}, format="json")
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)
        self.assertIn(complete_response.data["status"], ["completed", "promoted"])

        analysis_response = self.client.get(reverse("ai-experiment-analysis", args=[experiment_public_id]))
        self.assertEqual(analysis_response.status_code, status.HTTP_200_OK)
        self.assertEqual(analysis_response.data["primary_metric"], "usefulness_score")

    def test_tenant_scope_filters_experiments(self):
        experiment = Experiment.objects.create(
            name="Tenant scoped experiment",
            slug="tenant-scoped-experiment",
            description="Scoped",
            target_component=Experiment.TargetComponent.AGENT,
            target_reference="maintenance-agent",
            status=Experiment.Status.RUNNING,
            company=self.company,
            site=self.site,
            created_by_user=self.user,
        )
        other_membership = MembershipFactory()
        self._grant_access(other_membership.user, role_name="Other Governance")

        self.client.force_authenticate(other_membership.user)
        response = self.client.get(reverse("ai-experiment-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)
        self.assertTrue(Experiment.objects.filter(public_id=experiment.public_id).exists())

