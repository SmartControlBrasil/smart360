from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.access_control_center.models import PermissionAction, PermissionDomain, RolePermission
from apps.ai_agents_center.models import AgentActionProposal, AgentDefinition, AgentExecutionPolicy, AgentRun
from apps.ai_autonomous_ops.models import AutonomousExecution, AutonomousModeConfig
from apps.ai_decision_engine.services.orchestrator import DecisionOrchestrator
from apps.observability_center.models import SystemEventLog
from tests.factories.access_control import AccessRoleFactory, UserRoleAssignmentFactory
from tests.factories.core import MembershipFactory
from tests.factories.smart_system import AssetFactory, OperationalSiteFactory


class AutonomousOperationsApiTests(APITestCase):
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
        )
        self.config = AutonomousModeConfig.objects.create(
            company=self.company,
            is_enabled=True,
            mode_level=2,
            max_risk_level="low",
            allowed_action_types=["mark_asset_attention"],
            confidence_threshold_default="0.70",
        )
        self._grant_access(self.user)
        self.client.force_authenticate(self.user)

    def _grant_access(self, user, *, role_name="AI Governance"):
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

    def _autoexecution(self):
        proposal = AgentActionProposal.objects.create(
            agent_run=self.run,
            action_type="mark_asset_under_watch",
            target_entity="asset",
            target_entity_id=str(self.asset.public_id),
            title="Mark asset under watch",
            summary="Autoexec test",
            proposed_payload={"asset_public_id": str(self.asset.public_id), "attention_score": 84},
            priority="medium",
            approval_required=False,
        )
        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)
        return AutonomousExecution.objects.get(source_decision=decision)

    def test_list_executions_and_health_metrics(self):
        execution = self._autoexecution()

        list_response = self.client.get(reverse("ai-autonomy-execution-list"), {"company": self.company.id})
        health_response = self.client.get(reverse("ai-autonomy-execution-health"), {"company": self.company.id})

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(health_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["results"][0]["public_id"], str(execution.public_id))
        self.assertIn("success_rate", health_response.data)
        self.assertGreaterEqual(health_response.data["total_executions"], 1)

    def test_kill_switch_endpoint_updates_config_and_logs_event(self):
        response = self.client.post(
            reverse("ai-autonomy-config-kill-switch", args=[self.config.public_id]),
            {"enabled": True, "company": self.company.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.config.refresh_from_db()
        self.assertTrue(self.config.kill_switch_enabled)
        self.assertTrue(SystemEventLog.objects.filter(event_type="autonomy.kill_switch.activated").exists())

    def test_rollback_endpoint_reverts_supported_execution(self):
        execution = self._autoexecution()

        response = self.client.post(
            reverse("ai-autonomy-execution-rollback", args=[execution.public_id]),
            {"company": self.company.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        execution.refresh_from_db()
        self.assertEqual(execution.execution_status, AutonomousExecution.ExecutionStatus.ROLLED_BACK)

    def test_company_scope_hides_other_tenant_executions(self):
        self._autoexecution()
        other_membership = MembershipFactory()
        self._grant_access(other_membership.user, role_name="Other Governance")
        self.client.force_authenticate(other_membership.user)

        response = self.client.get(reverse("ai-autonomy-execution-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)
