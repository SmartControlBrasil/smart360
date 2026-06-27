from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.access_control_center.models import PermissionAction, PermissionDomain, RolePermission
from apps.ai_agents_center.models import AgentActionProposal, AgentDefinition, AgentExecutionPolicy, AgentRun
from apps.ai_decision_engine.services.orchestrator import DecisionOrchestrator
from apps.observability_center.models import SystemEventLog
from tests.factories.access_control import AccessRoleFactory, UserRoleAssignmentFactory
from tests.factories.core import MembershipFactory
from tests.factories.smart_system import AssetFactory, OperationalSiteFactory, ScheduledVisitFactory


class SimulationEngineApiTests(APITestCase):
    def setUp(self):
        self.membership = MembershipFactory()
        self.company = self.membership.company
        self.user = self.membership.user
        self.site = OperationalSiteFactory(maintenance_client__company=self.company)
        self.asset = AssetFactory(operational_site=self.site)
        self.agent = AgentDefinition.objects.create(
            slug="simulation-agent",
            name="Simulation Agent",
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
            agent_run=self.agent_run,
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

    def test_request_simulation_by_decision_runs_and_returns_result(self):
        decision = self._decision()

        response = self.client.post(
            reverse("ai-simulation-scenario-request"),
            {"decision_public_id": str(decision.public_id), "company": self.company.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["simulation_type"], "maintenance_action_plan_simulation")
        self.assertEqual(response.data["status"], "completed")
        self.assertIn("result", response.data)

    def test_compare_endpoint_returns_current_vs_proposed(self):
        visit = ScheduledVisitFactory(company=self.company, operational_site=self.site, asset=self.asset)
        response = self.client.post(
            reverse("ai-simulation-scenario-request"),
            {
                "simulation_type": "technician_reassignment_simulation",
                "company": self.company.id,
                "site": self.site.id,
                "target_entity": "scheduled_visit",
                "target_entity_id": str(visit.public_id),
                "input_payload": {"visit_public_id": str(visit.public_id), "to_technician_id": visit.technician_id},
            },
            format="json",
        )
        run_public_id = response.data["public_id"]

        compare_response = self.client.get(reverse("ai-simulation-run-compare", args=[run_public_id]), {"company": self.company.id})

        self.assertEqual(compare_response.status_code, status.HTTP_200_OK)
        self.assertIn("current", compare_response.data)
        self.assertIn("proposed", compare_response.data)
        self.assertTrue(SystemEventLog.objects.filter(event_type="simulation.viewed").exists())

    def test_by_entity_endpoint_returns_scoped_history(self):
        decision = self._decision()

        self.client.post(
            reverse("ai-simulation-scenario-request"),
            {"decision_public_id": str(decision.public_id), "company": self.company.id},
            format="json",
        )
        response = self.client.get(
            reverse("ai-simulation-run-by-entity"),
            {"company": self.company.id, "entity": "asset", "entity_id": str(self.asset.public_id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertTrue(all(item["simulation_type"] == "maintenance_action_plan_simulation" for item in response.data))

    def test_by_entity_endpoint_does_not_leak_other_company_history(self):
        other_membership = MembershipFactory()
        other_company = other_membership.company
        other_user = other_membership.user
        other_site = OperationalSiteFactory(maintenance_client__company=other_company)
        other_asset = AssetFactory(operational_site=other_site)
        other_run = AgentRun.objects.create(
            agent=self.agent,
            company=other_company,
            site=other_site,
            triggered_by=other_user,
            trigger_type=AgentRun.TriggerType.MANUAL,
            status=AgentRun.Status.COMPLETED,
        )
        other_proposal = AgentActionProposal.objects.create(
            agent_run=other_run,
            action_type="open_inspection_work_order",
            target_entity="asset",
            target_entity_id=str(other_asset.public_id),
            title="Open inspection work order",
            summary="Inspection required",
            proposed_payload={"asset_public_id": str(other_asset.public_id)},
            priority="high",
            approval_required=True,
        )
        DecisionOrchestrator.receive_action_proposal(proposal=other_proposal)

        response = self.client.get(
            reverse("ai-simulation-run-by-entity"),
            {"company": self.company.id, "entity": "asset", "entity_id": str(other_asset.public_id)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_attach_to_decision_endpoint_links_existing_run(self):
        response = self.client.post(
            reverse("ai-simulation-scenario-request"),
            {
                "simulation_type": "maintenance_action_plan_simulation",
                "company": self.company.id,
                "site": self.site.id,
                "target_entity": "asset",
                "target_entity_id": str(self.asset.public_id),
                "input_payload": {"asset_public_id": str(self.asset.public_id)},
            },
            format="json",
        )
        run_public_id = response.data["public_id"]
        decision = self._decision()
        decision.simulation_runs.all().delete()

        attach_response = self.client.post(
            reverse("ai-simulation-run-attach-to-decision", args=[run_public_id]),
            {"decision_public_id": str(decision.public_id), "company": self.company.id},
            format="json",
        )

        self.assertEqual(attach_response.status_code, status.HTTP_200_OK)
        decision.refresh_from_db()
        self.assertEqual(str(decision.simulation_runs.get().public_id), run_public_id)
        self.assertIn("simulation", decision.explainability_payload)

    def test_copilot_summary_endpoint_returns_recent_results(self):
        decision = self._decision()
        self.client.post(
            reverse("ai-simulation-scenario-request"),
            {"decision_public_id": str(decision.public_id), "company": self.company.id},
            format="json",
        )

        response = self.client.get(reverse("ai-simulation-run-copilot-summary"), {"company": self.company.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["results"])
