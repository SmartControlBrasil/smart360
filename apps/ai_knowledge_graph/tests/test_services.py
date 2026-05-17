from django.test import TestCase

from apps.access_control_center.services.smart_system_access import bootstrap_smart_system_access
from apps.ai_agents_center.models import AgentActionProposal, AgentDefinition, AgentRecommendation, AgentRun
from apps.ai_decision_engine.models import AgentDecision
from apps.ai_knowledge_graph.models import GraphEdge, GraphNode
from apps.ai_knowledge_graph.services.graph import GraphInsightService, GraphProjectionService, GraphQueryService
from apps.integration_bus.services.realtime_bus import RealtimeSubscriberRegistry
from apps.marketplace_technicians.models import TechnicianAssignment, TechnicianProfile, TechnicianServiceRequest, TechnicianSkill, TechnicianSkillAssignment
from apps.smart_system.models import FailureEvent, ServiceOrder
from tests.factories.core import UserFactory
from tests.factories.smart_system import (
    AssetCategoryFactory,
    AssetFactory,
    FailureEventFactory,
    MaintenanceClientFactory,
    MaintenanceContractFactory,
    MaintenancePlanFactory,
    OperationalSiteFactory,
    PartFactory,
    ServiceOrderFactory,
    StockMovementFactory,
)


class KnowledgeGraphServiceTests(TestCase):
    def setUp(self):
        bootstrap_smart_system_access()
        self.site = OperationalSiteFactory()
        self.company = self.site.maintenance_client.company
        self.category = AssetCategoryFactory(name="HVAC Critical")
        self.asset = AssetFactory(operational_site=self.site, category=self.category, criticality="critical")
        self.user = UserFactory(is_staff=True)
        self.order = ServiceOrderFactory(
            client=self.site.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            assigned_to=self.user,
            status=ServiceOrder.Status.COMPLETED,
        )
        self.failure = FailureEventFactory(asset=self.asset, service_order=self.order, severity=FailureEvent.Severity.CRITICAL)
        self.plan = MaintenancePlanFactory(asset=self.asset, operational_site=self.site, company=self.company)
        self.contract = MaintenanceContractFactory(company=self.company, client=self.site.maintenance_client, operational_site=self.site)
        self.part = PartFactory(company=self.company, operational_site=self.site)
        StockMovementFactory(company=self.company, operational_site=self.site, part=self.part, service_order=self.order)
        self.tech_profile = TechnicianProfile.objects.create(
            user=self.user,
            company=self.company,
            display_name="Tecnico KG",
            verification_status=TechnicianProfile.VerificationStatus.APPROVED,
            marketplace_status=TechnicianProfile.MarketplaceStatus.AVAILABLE,
            rating_average="4.90",
            completed_jobs_count=20,
        )
        self.skill = TechnicianSkill.objects.create(name="HVAC")
        TechnicianSkillAssignment.objects.create(technician_profile=self.tech_profile, skill=self.skill, proficiency_level="specialist", years_experience=8)
        self.request = TechnicianServiceRequest.objects.create(
            requester_user=self.user,
            requester_company=self.company,
            title="Atendimento HVAC",
            description="Falha de chiller",
            category="hvac",
            service_type=TechnicianServiceRequest.ServiceType.MAINTENANCE,
            priority=TechnicianServiceRequest.Priority.HIGH,
            city="Sao Paulo",
            state="SP",
            related_client=self.site.maintenance_client,
            related_site=self.site,
            related_asset=self.asset,
            related_service_order=self.order,
        )
        TechnicianAssignment.objects.create(
            technician_service_request=self.request,
            technician_profile=self.tech_profile,
        )
        self.agent = AgentDefinition.objects.create(
            slug="maintenance-agent-kg",
            name="Maintenance KG Agent",
            domain=AgentDefinition.Domain.MAINTENANCE,
            status=AgentDefinition.Status.ACTIVE,
        )
        self.run = AgentRun.objects.create(
            agent=self.agent,
            trigger_type=AgentRun.TriggerType.EVENT,
            trigger_reference=f"failure:{self.failure.public_id}",
            company=self.company,
            site=self.site,
            status=AgentRun.Status.COMPLETED,
        )
        self.recommendation = AgentRecommendation.objects.create(
            agent_run=self.run,
            company=self.company,
            site=self.site,
            asset=self.asset,
            recommendation_type=AgentRecommendation.RecommendationType.FAILURE_PATTERN_ALERT,
            title="Investigar modo de falha",
            summary="Falha se repete em ativos HVAC criticos.",
            severity=AgentRecommendation.Severity.HIGH,
            priority=AgentRecommendation.Priority.HIGH,
        )
        self.proposal = AgentActionProposal.objects.create(
            agent_run=self.run,
            action_type="create_investigation_task",
            target_entity="asset",
            target_entity_id=str(self.asset.public_id),
            title="Criar investigacao",
            summary="Abrir tarefa tecnica",
        )
        self.decision = AgentDecision.objects.create(
            agent_action_proposal=self.proposal,
            company=self.company,
            site=self.site,
            action_type="create_investigation_task",
            normalized_action_type="create_investigation_task",
            target_entity="asset",
            target_entity_id=str(self.asset.public_id),
            risk_level="medium",
            decision_status="approved",
        )

    def test_projection_creates_nodes_and_edges(self):
        run = GraphProjectionService.project_company_graph(company=self.company, site=self.site)
        self.assertEqual(run.status, "completed")
        self.assertTrue(GraphNode.objects.filter(company=self.company, node_type="asset").exists())
        self.assertTrue(GraphEdge.objects.filter(company=self.company, edge_type="asset_has_failure").exists())

    def test_relational_queries_return_context(self):
        GraphProjectionService.project_company_graph(company=self.company, site=self.site)
        failures = GraphQueryService.related_failures(company=self.company, asset_public_id=self.asset.public_id)
        technicians = GraphQueryService.related_technicians(company=self.company, asset_public_id=self.asset.public_id)
        parts = GraphQueryService.related_parts(company=self.company, asset_public_id=self.asset.public_id)
        self.assertGreaterEqual(len(failures), 1)
        self.assertGreaterEqual(len(technicians), 1)
        self.assertGreaterEqual(len(parts), 1)

    def test_graph_insight_is_generated(self):
        GraphProjectionService.project_company_graph(company=self.company, site=self.site)
        insight = GraphInsightService.insights_for_entity(company=self.company, entity_type="asset", entity_public_id=self.asset.public_id)
        self.assertIn("summary", insight)
        self.assertGreaterEqual(len(insight.get("top_relations", [])), 1)

    def test_reactive_event_runs_projection(self):
        event = self.company.integration_events.create(
            event_name="failures.created",
            event_version=1,
            source_module="smart_system",
            event_type="domain",
            company=self.company,
            site=self.site,
            aggregate_type="failure_event",
            aggregate_id=str(self.failure.public_id),
            payload={"asset_public_id": str(self.asset.public_id)},
            metadata={},
            request_id="graph-reactive-1",
            priority="high",
            status="published",
        )
        result = RealtimeSubscriberRegistry.knowledge_graph_projection_refresh(event=event)
        self.assertEqual(result.status, "delivered")
        self.assertTrue(GraphNode.objects.filter(company=self.company, node_type="failure_event").exists())

