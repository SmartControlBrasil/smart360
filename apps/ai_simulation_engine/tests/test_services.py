from django.test import TestCase
from django.utils import timezone

from apps.access_control_center.models import PermissionAction, PermissionDomain, RolePermission
from apps.ai_agents_center.models import AgentActionProposal, AgentDefinition, AgentExecutionPolicy, AgentRun
from apps.ai_decision_engine.services.approvals import DecisionApprovalService
from apps.ai_decision_engine.services.orchestrator import DecisionOrchestrator
from apps.ai_simulation_engine.models import SimulationRun, SimulationScenario, SimulationType
from apps.ai_simulation_engine.services.orchestrator import SimulationOrchestrator
from apps.observability_center.models import SystemEventLog
from tests.factories.access_control import AccessRoleFactory, UserRoleAssignmentFactory
from tests.factories.core import MembershipFactory, UserFactory
from tests.factories.marketplace_technicians import (
    TechnicianMatchingRecordFactory,
    TechnicianProfileFactory,
    TechnicianServiceRequestFactory,
)
from tests.factories.smart_system import (
    AssetFactory,
    FailureEventFactory,
    MaintenanceContractFactory,
    MaintenancePlanFactory,
    OperationalSiteFactory,
    ScheduledVisitFactory,
    TechnicianScheduleFactory,
)


class SimulationEngineServiceTests(TestCase):
    def setUp(self):
        self.membership = MembershipFactory()
        self.company = self.membership.company
        self.user = self.membership.user
        self.site = OperationalSiteFactory(maintenance_client__company=self.company)
        self.asset = AssetFactory(operational_site=self.site, criticality="high")
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
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )

    def _grant_access(self, user, *, role_name="Maintenance Manager"):
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

    def _run_manual_simulation(self, *, slug, input_payload, target_entity="asset", target_entity_id=""):
        simulation_type = SimulationType.objects.get(slug=slug)
        scenario = SimulationScenario.objects.create(
            simulation_type=simulation_type,
            company=self.company,
            site=self.site,
            title=f"Scenario {slug}",
            description="Simulation test",
            target_entity=target_entity,
            target_entity_id=target_entity_id,
            status=SimulationScenario.ScenarioStatus.READY,
            created_by_user=self.user,
        )
        simulation_run = SimulationRun.objects.create(
            scenario=scenario,
            trigger_type=SimulationRun.TriggerType.MANUAL,
            source_type=SimulationRun.SourceType.DIRECT,
            input_payload=input_payload,
            created_by_user=self.user,
        )
        return SimulationOrchestrator.run(simulation_run=simulation_run)

    def _proposal(self, *, action_type, target_entity="asset", target_entity_id=None, payload=None, priority="high"):
        return AgentActionProposal.objects.create(
            agent_run=self.agent_run,
            action_type=action_type,
            target_entity=target_entity,
            target_entity_id=target_entity_id or str(self.asset.public_id),
            title=f"Proposal {action_type}",
            summary=f"Summary for {action_type}",
            proposed_payload=payload or {"asset_public_id": str(self.asset.public_id)},
            priority=priority,
            approval_required=True,
        )

    def test_route_reorder_simulation_persists_baseline_and_comparison(self):
        technician = UserFactory()
        target_date = timezone.localdate()
        ScheduledVisitFactory(
            company=self.company,
            operational_site=self.site,
            asset=self.asset,
            technician=technician,
            scheduled_date=target_date,
            route_order=3,
            estimated_travel_minutes=35,
            priority="urgent",
        )
        ScheduledVisitFactory(
            company=self.company,
            operational_site=self.site,
            asset=self.asset,
            technician=technician,
            scheduled_date=target_date,
            route_order=1,
            estimated_travel_minutes=15,
            priority="medium",
        )
        ScheduledVisitFactory(
            company=self.company,
            operational_site=self.site,
            asset=self.asset,
            technician=technician,
            scheduled_date=target_date,
            route_order=2,
            estimated_travel_minutes=20,
            priority="high",
        )

        simulation_run = self._run_manual_simulation(
            slug="route_reorder_simulation",
            input_payload={"date": target_date.isoformat(), "technician_id": technician.id},
            target_entity="technician",
            target_entity_id=str(technician.id),
        )

        self.assertEqual(simulation_run.status, SimulationRun.RunStatus.COMPLETED)
        self.assertEqual(len(simulation_run.baseline_snapshot["visits"]), 3)
        self.assertIn("current", simulation_run.result.result_payload)
        self.assertIn("proposed", simulation_run.result.result_payload)
        self.assertTrue(SystemEventLog.objects.filter(event_type="simulation.run.completed").exists())

    def test_technician_reassignment_simulation_returns_schedule_impact(self):
        from_tech = UserFactory()
        to_tech = UserFactory()
        visit = ScheduledVisitFactory(
            company=self.company,
            operational_site=self.site,
            asset=self.asset,
            technician=from_tech,
            scheduled_date=timezone.localdate(),
        )
        TechnicianScheduleFactory(company=self.company, operational_site=self.site, technician=from_tech, date=visit.scheduled_date, total_jobs=5)
        TechnicianScheduleFactory(company=self.company, operational_site=self.site, technician=to_tech, date=visit.scheduled_date, total_jobs=2)

        simulation_run = self._run_manual_simulation(
            slug="technician_reassignment_simulation",
            input_payload={"visit_public_id": str(visit.public_id), "from_technician_id": from_tech.id, "to_technician_id": to_tech.id},
            target_entity="scheduled_visit",
            target_entity_id=str(visit.public_id),
        )

        self.assertEqual(simulation_run.result.result_payload["current"]["from_jobs"], 5.0)
        self.assertEqual(simulation_run.result.result_payload["proposed"]["to_jobs"], 3.0)
        self.assertGreater(simulation_run.result.workload_delta, 0)

    def test_preventive_frequency_simulation_returns_plausible_risk_and_cost(self):
        MaintenancePlanFactory(asset=self.asset, company=self.company, operational_site=self.site, estimated_duration_minutes=120)
        FailureEventFactory(asset=self.asset)
        FailureEventFactory(asset=self.asset)

        simulation_run = self._run_manual_simulation(
            slug="preventive_frequency_change_simulation",
            input_payload={"asset_public_id": str(self.asset.public_id), "proposed_frequency_days": 15},
            target_entity="asset",
            target_entity_id=str(self.asset.public_id),
        )

        self.assertLess(simulation_run.result.risk_delta, 0)
        self.assertGreater(simulation_run.result.cost_delta, 0)
        self.assertEqual(simulation_run.baseline_snapshot["current_frequency_days"], 30.0)

    def test_contract_repricing_simulation_returns_margin_change(self):
        contract = MaintenanceContractFactory(company=self.company, operational_site=self.site, client=self.site.maintenance_client, contract_value=1000)

        simulation_run = self._run_manual_simulation(
            slug="contract_repricing_simulation",
            input_payload={"contract_public_id": str(contract.public_id), "proposed_value": "1200.00", "current_margin": "12.00"},
            target_entity="maintenance_contract",
            target_entity_id=str(contract.public_id),
        )

        self.assertIn("margem", simulation_run.result.summary.lower())
        self.assertGreater(simulation_run.result.impact_score, 0)
        self.assertGreater(simulation_run.result.profit_delta, 0)

    def test_asset_scoping_blocks_cross_company_simulation_access(self):
        other_membership = MembershipFactory()
        other_site = OperationalSiteFactory(maintenance_client__company=other_membership.company)
        other_asset = AssetFactory(operational_site=other_site)

        with self.assertRaises(Exception):
            self._run_manual_simulation(
                slug="maintenance_action_plan_simulation",
                input_payload={"asset_public_id": str(other_asset.public_id)},
                target_entity="asset",
                target_entity_id=str(other_asset.public_id),
            )

    def test_decision_integration_attaches_required_simulation_result(self):
        proposal = self._proposal(
            action_type="open_inspection_work_order",
            payload={"asset_public_id": str(self.asset.public_id), "maintenance_type": "inspection"},
        )

        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)

        self.assertIn("simulation_requirement", decision.explainability_payload)
        self.assertIn("simulation", decision.explainability_payload)
        self.assertEqual(decision.simulation_runs.filter(status=SimulationRun.RunStatus.COMPLETED).count(), 1)

    def test_decision_approval_is_blocked_when_required_simulation_is_missing(self):
        proposal = self._proposal(
            action_type="open_inspection_work_order",
            payload={"asset_public_id": str(self.asset.public_id), "maintenance_type": "inspection"},
        )
        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)
        decision.simulation_runs.all().delete()
        approver = UserFactory()
        self._grant_access(approver)

        with self.assertRaises(PermissionError):
            DecisionApprovalService.approve(decision=decision, approved_by=approver, comment="approve without simulation", execute=False)

    def test_marketplace_candidate_swap_simulation_returns_matching_comparison(self):
        request = TechnicianServiceRequestFactory(requester_company=self.company, related_site=self.site, related_asset=self.asset)
        current_candidate = TechnicianProfileFactory(company=self.company)
        proposed_candidate = TechnicianProfileFactory(company=self.company)
        TechnicianMatchingRecordFactory(
            technician_service_request=request,
            technician_profile=current_candidate,
            match_score="78.00",
            ranking_position=1,
        )
        TechnicianMatchingRecordFactory(
            technician_service_request=request,
            technician_profile=proposed_candidate,
            match_score="91.00",
            ranking_position=2,
        )

        simulation_run = self._run_manual_simulation(
            slug="marketplace_candidate_swap_simulation",
            input_payload={
                "service_request_public_id": str(request.public_id),
                "current_candidate_public_id": str(current_candidate.public_id),
                "proposed_candidate_public_id": str(proposed_candidate.public_id),
            },
            target_entity="technician_service_request",
            target_entity_id=str(request.public_id),
        )

        self.assertEqual(simulation_run.result.result_payload["current"]["match_score"], "78.00")
        self.assertEqual(simulation_run.result.result_payload["proposed"]["match_score"], "91.00")
