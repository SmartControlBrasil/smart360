from django.test import TestCase
from django.utils import timezone

from apps.access_control_center.models import PermissionAction, PermissionDomain, RolePermission
from apps.ai_agents_center.models import AgentActionProposal, AgentDefinition, AgentExecutionPolicy, AgentRun
from apps.ai_decision_engine.models import AgentDecision, DecisionApproval, DecisionExecution, DecisionPolicy
from apps.ai_decision_engine.services.approvals import DecisionApprovalService
from apps.ai_decision_engine.services.orchestrator import DecisionOrchestrator
from apps.observability_center.models import SystemEventLog
from tests.factories.access_control import AccessRoleFactory, UserRoleAssignmentFactory
from tests.factories.core import MembershipFactory, UserFactory
from tests.factories.marketplace_technicians import TechnicianProfileFactory, TechnicianServiceRequestFactory
from tests.factories.smart_system import AssetFactory, OperationalSiteFactory


class DecisionEngineServiceTests(TestCase):
    def setUp(self):
        self.company_membership = MembershipFactory()
        self.company = self.company_membership.company
        self.user = self.company_membership.user
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

    def _grant_decision_access(self, *, user, role_name="Maintenance Manager", action_names=("view", "approve")):
        domain, _ = PermissionDomain.objects.get_or_create(
            slug="ai_agents_admin",
            defaults={
                "name": "ai_agents_admin",
                "description": "AI Agents admin access",
                "module_name": "ai_agents_center",
                "is_active": True,
            },
        )
        role = AccessRoleFactory(name=role_name)
        for action_name in action_names:
            action, _ = PermissionAction.objects.get_or_create(domain=domain, action_name=action_name, defaults={"is_active": True})
            RolePermission.objects.get_or_create(
                role=role,
                permission_domain=domain,
                permission_action=action,
                defaults={"is_allowed": True},
            )
        UserRoleAssignmentFactory(user=user, role=role, company=self.company)
        return role

    def _proposal(self, *, action_type, target_entity="asset", target_entity_id=None, payload=None, priority="medium"):
        return AgentActionProposal.objects.create(
            agent_run=self.run,
            action_type=action_type,
            target_entity=target_entity,
            target_entity_id=target_entity_id or str(self.asset.public_id),
            title=f"Proposal {action_type}",
            summary=f"Summary for {action_type}",
            proposed_payload=payload or {"asset_public_id": str(self.asset.public_id)},
            priority=priority,
            approval_required=True,
        )

    def test_low_risk_safe_action_autoexecutes_and_is_audited(self):
        proposal = self._proposal(
            action_type="mark_asset_under_watch",
            payload={"asset_public_id": str(self.asset.public_id), "attention_score": 82},
            priority="medium",
        )

        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)

        self.assertEqual(decision.normalized_action_type, "mark_asset_attention")
        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.EXECUTED)
        self.assertEqual(proposal.status, AgentActionProposal.Status.EXECUTED)
        self.assertTrue(decision.executions.filter(execution_status=DecisionExecution.ExecutionStatus.SUCCEEDED).exists())
        self.assertTrue(SystemEventLog.objects.filter(event_type="decision.auto_approved").exists())
        self.assertTrue(SystemEventLog.objects.filter(event_type="decision.execution.succeeded").exists())

    def test_high_risk_action_goes_to_human_approval(self):
        proposal = self._proposal(
            action_type="open_inspection_work_order",
            payload={"asset_public_id": str(self.asset.public_id), "maintenance_type": "inspection"},
            priority="high",
        )

        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)

        self.assertEqual(decision.normalized_action_type, "create_work_order_proposal")
        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.AWAITING_APPROVAL)
        self.assertTrue(decision.approvals.filter(approval_status=DecisionApproval.ApprovalStatus.PENDING).exists())
        self.assertEqual(proposal.status, AgentActionProposal.Status.PENDING_APPROVAL)

    def test_user_without_permission_cannot_approve(self):
        proposal = self._proposal(action_type="open_inspection_work_order", priority="high")
        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)
        unauthorized = UserFactory()

        with self.assertRaises(PermissionError):
            DecisionApprovalService.approve(decision=decision, approved_by=unauthorized, comment="should fail", execute=True)

    def test_approved_decision_executes_within_company_context(self):
        proposal = self._proposal(action_type="open_inspection_work_order", priority="high")
        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)
        approver = UserFactory()
        self._grant_decision_access(user=approver, role_name="Maintenance Manager")

        DecisionOrchestrator.approve_decision(decision=decision, approved_by=approver, comment="approved")
        decision.refresh_from_db()

        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.EXECUTED)
        execution = decision.executions.latest("created_at")
        self.assertEqual(execution.execution_status, DecisionExecution.ExecutionStatus.SUCCEEDED)
        self.assertEqual(execution.decision.company, self.company)
        self.assertIn("order_number", execution.result_payload)

    def test_execution_failure_is_persisted_and_observable(self):
        policy = DecisionPolicy.objects.get(action_type="assign_marketplace_candidate_proposal")
        policy.approver_role_slugs = ["coordinator"]
        policy.save(update_fields=["approver_role_slugs", "updated_at"])
        proposal = AgentActionProposal.objects.create(
            agent_run=self.run,
            action_type="assign_recommended_marketplace_technician",
            target_entity="technician_service_request",
            target_entity_id="00000000-0000-0000-0000-000000000000",
            title="Assign marketplace candidate",
            summary="Assignment should fail due missing request",
            proposed_payload={"service_request_public_id": "00000000-0000-0000-0000-000000000000"},
            priority="high",
            approval_required=True,
        )
        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)
        approver = UserFactory()
        self._grant_decision_access(user=approver, role_name="Coordinator")

        with self.assertRaises(Exception):
            DecisionOrchestrator.approve_decision(decision=decision, approved_by=approver, comment="execute anyway")

        decision.refresh_from_db()
        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.FAILED)
        self.assertTrue(decision.executions.filter(execution_status=DecisionExecution.ExecutionStatus.FAILED).exists())
        self.assertTrue(SystemEventLog.objects.filter(event_type="decision.execution.failed").exists())

    def test_marketplace_agent_proposal_is_normalized_and_persists_history(self):
        marketplace_agent = AgentDefinition.objects.create(
            slug="marketplace-agent",
            name="Marketplace Agent",
            domain=AgentDefinition.Domain.MARKETPLACE,
            status=AgentDefinition.Status.ACTIVE,
            autonomy_level=AgentDefinition.AutonomyLevel.PROPOSE,
            enabled=True,
        )
        AgentExecutionPolicy.objects.create(agent=marketplace_agent, require_human_approval=True)
        service_request = TechnicianServiceRequestFactory(requester_company=self.company, related_site=self.site, related_asset=self.asset)
        technician_profile = TechnicianProfileFactory(company=self.company)
        run = AgentRun.objects.create(
            agent=marketplace_agent,
            company=self.company,
            site=self.site,
            triggered_by=self.user,
            trigger_type=AgentRun.TriggerType.EVENT,
            status=AgentRun.Status.COMPLETED,
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )
        proposal = AgentActionProposal.objects.create(
            agent_run=run,
            action_type="suggest_alternative_technician_via_matching",
            target_entity="technician_service_request",
            target_entity_id=str(service_request.public_id),
            title="Suggest alternative technician",
            summary="Need a marketplace assignment proposal",
            proposed_payload={
                "service_request_public_id": str(service_request.public_id),
                "marketplace_candidates": [{"technician_profile_public_id": str(technician_profile.public_id)}],
            },
            priority="high",
            approval_required=True,
        )

        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)

        self.assertEqual(decision.normalized_action_type, "assign_marketplace_candidate_proposal")
        self.assertGreaterEqual(decision.audit_entries.count(), 2)
