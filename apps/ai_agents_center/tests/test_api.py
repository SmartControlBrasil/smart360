import json
from decimal import Decimal
from unittest.mock import patch
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.ai_agents_center.models import AIBriefing, AgentActionProposal, AgentAssetAttentionFlag, AgentMarketplaceRequestFlag, AgentProfitabilityAttentionFlag, AgentRecommendation, AgentRun
from apps.ai_agents_center.models import AgentAnomalyAttentionFlag, CommercialOpportunity, ManagerCopilotMessage, ManagerCopilotSession
from apps.analytics_platform.models import ContractProfitability, OperationalMetrics
from apps.analytics_platform.services.analytics_service import ExecutiveAnalyticsService
from apps.ai_agents_center.services.orchestrator import AgentCoordinatorService
from apps.ai_agents_center.services.registry import AgentRegistryService
from apps.ai_agents_center.services.briefing_composer import AIBriefingComposer
from apps.observability_center.models import SystemEventLog
from apps.smart_system.models import FailureEvent, ServiceOrder
from tests.factories.core import CompanyFactory, MembershipFactory, UserFactory
from tests.factories.marketplace_technicians import TechnicianProfileFactory
from tests.factories.marketplace_technicians import (
    ServiceRegionFactory,
    TechnicianAvailabilityFactory,
    TechnicianMatchingRecordFactory,
    TechnicianServiceRegionFactory,
    TechnicianServiceRequestFactory,
    TechnicianSkillAssignmentFactory,
    TechnicianSkillFactory,
)
def _payload_items(response):
    if isinstance(response.data, list):
        return response.data
    if isinstance(response.data, dict):
        return response.data.get("results", [])
    return []


from tests.factories.smart_system import (
    AssetCategoryFactory,
    AssetFactory,
    ChecklistFactory,
    ChecklistItemFactory,
    MaintenanceContractFactory,
    MaintenanceClientFactory,
    MaintenancePlanFactory,
    OperationalSiteFactory,
    PartFactory,
    ScheduledVisitFactory,
    ServiceQuoteFactory,
    ServiceOrderChecklistResponseFactory,
    ServiceOrderFactory,
    StockMovementFactory,
    TechnicianAvailabilityWindowFactory,
    TechnicianScheduleFactory,
    WorkLogFactory,
)


class AIAgentsCenterApiTests(APITestCase):
    def setUp(self):
        bootstrap_smart_system_access()
        AgentRegistryService.bootstrap_registry()

        self.user = UserFactory(email="agents@smart360.local", password="StrongPass123")
        self.company = CompanyFactory(name="AI Agents Company", slug="ai-agents-company")
        MembershipFactory(user=self.user, company=self.company, is_primary=True)
        assign_smart_system_role(self.user, "maintenance-manager", company=self.company)
        self.client.force_authenticate(self.user)

        self.maintenance_client = MaintenanceClientFactory(company=self.company, display_name="Cliente AI")
        self.site = OperationalSiteFactory(maintenance_client=self.maintenance_client, name="Unidade AI", code="AI-01")
        self.asset = AssetFactory(
            operational_site=self.site,
            category=AssetCategoryFactory(name="HVAC AI"),
            asset_tag="AI-AST-01",
            name="Chiller AI",
        )
        self.order = ServiceOrderFactory(
            order_number="OS-AI-001",
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            assigned_to=self.user,
            created_by=self.user,
            maintenance_type="corrective",
            priority="high",
            title="Falha recorrente AI",
        )
        FailureEvent.objects.create(
            asset=self.asset,
            service_order=self.order,
            symptom="Oscilacao termica",
            probable_cause="Sensor",
            severity="high",
        )
        FailureEvent.objects.create(
            asset=self.asset,
            service_order=self.order,
            symptom="Falha de leitura",
            probable_cause="Cabeamento",
            severity="high",
        )
        self.plan = MaintenancePlanFactory(
            asset=self.asset,
            company=self.company,
            operational_site=self.site,
            next_due_date=timezone.localdate() - timedelta(days=3),
        )
        self.checklist = ChecklistFactory(company=self.company, operational_site=self.site, name="Checklist AI")
        self.checklist_item = ChecklistItemFactory(checklist=self.checklist, title="Temperatura")
        ServiceOrderChecklistResponseFactory(service_order=self.order, checklist_item=self.checklist_item, response_boolean=False)
        self.secondary_technician = UserFactory(email="dispatch2@smart360.local", password="StrongPass123")
        MembershipFactory(user=self.secondary_technician, company=self.company, is_primary=False)
        assign_smart_system_role(self.secondary_technician, "maintenance-manager", company=self.company)
        self.primary_profile = TechnicianProfileFactory(user=self.user, company=self.company, display_name="Tecnico Joao")
        self.secondary_profile = TechnicianProfileFactory(user=self.secondary_technician, company=self.company, display_name="Tecnica Ana")
        TechnicianAvailabilityWindowFactory(company=self.company, operational_site=self.site, technician=self.user, max_daily_jobs=4, max_daily_hours=8)
        TechnicianAvailabilityWindowFactory(company=self.company, operational_site=self.site, technician=self.secondary_technician, max_daily_jobs=6, max_daily_hours=8)

    def test_registry_exposes_default_agents(self):
        response = self.client.get(reverse("ai-agents-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(item["slug"] == "maintenance-agent" for item in _payload_items(response)))
        self.assertTrue(any(item["slug"] == "atlas-commercial-intelligence-agent" for item in _payload_items(response)))

    def test_briefing_generation_personalizes_by_audience(self):
        technician_briefing = AIBriefingComposer.generate_briefing(
            briefing_type=AIBriefing.BriefingType.DAILY_FIELD,
            audience=AIBriefing.Audience.TECHNICIAN,
            company=self.company,
            user=self.user,
        )
        client_user = UserFactory(email="cliente@smart360.local", password="StrongPass123", user_type="client")
        MembershipFactory(user=client_user, company=self.company, is_primary=False)
        assign_smart_system_role(client_user, "client-manager", company=self.company)
        client_briefing = AIBriefingComposer.generate_briefing(
            briefing_type=AIBriefing.BriefingType.DAILY_CLIENT,
            audience=AIBriefing.Audience.CLIENT,
            company=self.company,
            user=client_user,
        )

        self.assertIn("Agenda", technician_briefing.summary)
        self.assertNotIn("margem", client_briefing.summary.lower())
        self.assertEqual(client_briefing.audience, AIBriefing.Audience.CLIENT)

    def test_briefing_api_generates_and_lists_briefings(self):
        response = self.client.post(
            reverse("ai-agent-briefing-generate"),
            {"briefing_type": "daily_executive", "audience": "manager", "company": self.company.id, "site": self.site.id},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(AIBriefing.objects.filter(company=self.company, audience="manager").exists())

        list_response = self.client.get(reverse("ai-agent-briefings-list"), {"company": self.company.id})
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(_payload_items(list_response)), 1)

    def test_briefing_generation_handles_missing_problematic_assets(self):
        analytics_payload = {
            "summary_cards": [
                {"label": "Receita", "value": Decimal("1000.00")},
                {"label": "Custo", "value": Decimal("600.00")},
                {"label": "Margem", "value": "40%"},
                {"label": "SLA", "value": "95%"},
                {"label": "Preventivas", "value": 3},
                {"label": "Backlog", "value": 2},
            ],
        }

        with patch.object(ExecutiveAnalyticsService, "build_executive_dashboard", return_value=analytics_payload):
            briefing = AIBriefingComposer.generate_briefing(
                briefing_type=AIBriefing.BriefingType.DAILY_EXECUTIVE,
                audience=AIBriefing.Audience.MANAGER,
                company=self.company,
                user=self.user,
            )

        self.assertIn("0 ativos problemáticos", briefing.summary)
        self.assertEqual(briefing.content["cards"][2]["value"], 2)

    def test_briefing_scope_respects_company(self):
        other_company = CompanyFactory(name="Other AI", slug="other-ai")
        other_user = UserFactory(email="other@smart360.local", password="StrongPass123")
        MembershipFactory(user=other_user, company=other_company, is_primary=True)
        assign_smart_system_role(other_user, "maintenance-manager", company=other_company)
        other_briefing = AIBriefingComposer.generate_briefing(
            briefing_type=AIBriefing.BriefingType.DAILY_EXECUTIVE,
            audience=AIBriefing.Audience.MANAGER,
            company=other_company,
            user=other_user,
        )

        response = self.client.get(reverse("ai-agent-briefings-list"))

        public_ids = [item["public_id"] for item in _payload_items(response)]
        self.assertNotIn(str(other_briefing.public_id), public_ids)

    def test_briefing_delivery_creates_in_app_delivery(self):
        briefing = AIBriefingComposer.generate_briefing(
            briefing_type=AIBriefing.BriefingType.DAILY_FIELD,
            audience=AIBriefing.Audience.TECHNICIAN,
            company=self.company,
            user=self.user,
        )

        AIBriefingComposer.deliver_briefing(briefing=briefing, channels=["in_app"])

        self.assertTrue(briefing.deliveries.filter(channel="in_app", status="delivered").exists())

    def test_briefing_mark_viewed_updates_status_and_observability(self):
        briefing = AIBriefingComposer.generate_briefing(
            briefing_type=AIBriefing.BriefingType.DAILY_EXECUTIVE,
            audience=AIBriefing.Audience.MANAGER,
            company=self.company,
            user=self.user,
        )

        response = self.client.post(reverse("ai-agent-briefing-viewed", kwargs={"briefing_public_id": briefing.public_id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        briefing.refresh_from_db()
        self.assertEqual(briefing.status, AIBriefing.Status.VIEWED)
        self.assertTrue(SystemEventLog.objects.filter(event_type="briefing.viewed").exists())

    def test_manual_run_creates_run_recommendation_and_proposal(self):
        response = self.client.post(
            reverse("ai-agent-manual-run"),
            {
                "agent_slug": "maintenance-agent",
                "company": self.company.id,
                "site": self.site.id,
                "trigger_reference": self.order.order_number,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(AgentRun.objects.filter(agent__slug="maintenance-agent", company=self.company).exists())
        self.assertTrue(AgentRecommendation.objects.filter(agent_run__agent__slug="maintenance-agent", company=self.company).exists())
        self.assertTrue(AgentActionProposal.objects.filter(agent_run__agent__slug="maintenance-agent").exists())
        recommendation = AgentRecommendation.objects.filter(agent_run__agent__slug="maintenance-agent", company=self.company).latest("created_at")
        self.assertTrue(recommendation.explanation)
        self.assertTrue(recommendation.evidence_summary)
        self.assertTrue(recommendation.suggested_action)

    def test_manual_run_without_manage_permission_is_forbidden(self):
        limited_user = UserFactory(email="planner-ai@smart360.local", password="StrongPass123")
        MembershipFactory(user=limited_user, company=self.company, is_primary=True)
        assign_smart_system_role(limited_user, "planner", company=self.company)
        self.client.force_authenticate(limited_user)

        response = self.client.post(
            reverse("ai-agent-manual-run"),
            {"agent_slug": "maintenance-agent", "company": self.company.id, "site": self.site.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(AgentRun.objects.filter(agent__slug="maintenance-agent", triggered_by=limited_user).exists())
        self.client.force_authenticate(self.user)

    def test_atlas_agent_qualifies_public_opportunity_for_growth_engine(self):
        trigger_reference = json.dumps(
            {
                "empresa": "Hospital Exemplo",
                "segmento": "Hospital",
                "cidade": "Sao Paulo",
                "estado": "SP",
                "site": "https://hospital.example.com.br",
                "contatos_institucionais": ["contato@hospital.example.com.br"],
                "problemas": ["alto fluxo de limpeza e higienizacao em areas comuns"],
                "evidencias": ["Site institucional informa atendimento hospitalar 24 horas"],
                "presenca_digital": "site institucional ativo",
            }
        )

        run = AgentCoordinatorService.run_agent(
            agent_slug="atlas-commercial-intelligence-agent",
            company=self.company,
            triggered_by=self.user,
            trigger_reference=trigger_reference,
        )

        self.assertEqual(run.status, AgentRun.Status.COMPLETED)
        recommendation = AgentRecommendation.objects.filter(agent_run__agent__slug="atlas-commercial-intelligence-agent").latest("created_at")
        proposal = AgentActionProposal.objects.filter(agent_run__agent__slug="atlas-commercial-intelligence-agent").latest("created_at")
        opportunity = CommercialOpportunity.objects.get(company_name="Hospital Exemplo")
        self.assertEqual(recommendation.payload["score"]["label"], "Estrategico")
        self.assertEqual(proposal.action_type, "review_commercial_opportunity")
        self.assertEqual(proposal.target_entity_id, str(opportunity.public_id))
        self.assertEqual(opportunity.agent_run, run)
        self.assertIn("HygiBot", opportunity.recommended_product)

    def test_agent_detects_recurring_failure_pattern(self):
        FailureEvent.objects.create(
            asset=self.asset,
            service_order=self.order,
            symptom="Falha eletrica intermitente",
            probable_cause="Conector",
            severity="high",
        )
        response = self.client.post(
            reverse("ai-agent-manual-run"),
            {"agent_slug": "maintenance-agent", "company": self.company.id, "site": self.site.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="maintenance-agent",
                recommendation_type="failure_pattern_alert",
                entity_id=str(self.asset.public_id),
            ).exists()
        )

    def test_agent_does_not_detect_recurring_failure_pattern_below_threshold(self):
        response = self.client.post(
            reverse("ai-agent-manual-run"),
            {"agent_slug": "maintenance-agent", "company": self.company.id, "site": self.site.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="maintenance-agent",
                recommendation_type="failure_pattern_alert",
                entity_id=str(self.asset.public_id),
            ).exists()
        )

    def test_agent_detects_overdue_preventive_for_critical_asset(self):
        self.asset.criticality = "critical"
        self.asset.save(update_fields=["criticality", "updated_at"])
        response = self.client.post(
            reverse("ai-agent-manual-run"),
            {"agent_slug": "maintenance-agent", "company": self.company.id, "site": self.site.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="maintenance-agent",
                recommendation_type="critical_asset_watch",
                severity="critical",
                entity_id=str(self.asset.public_id),
            ).exists()
        )

    def test_agent_detects_consecutive_checklist_nok(self):
        second_order = ServiceOrderFactory(
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            assigned_to=self.user,
            created_by=self.user,
            maintenance_type="inspection",
            priority="high",
            status="completed",
        )
        ServiceOrderChecklistResponseFactory(service_order=second_order, checklist_item=self.checklist_item, response_boolean=False)

        response = self.client.post(
            reverse("ai-agent-manual-run"),
            {"agent_slug": "maintenance-agent", "company": self.company.id, "site": self.site.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="maintenance-agent",
                recommendation_type="extraordinary_inspection",
                entity_id=str(self.asset.public_id),
            ).exists()
        )

    def test_agent_creates_attention_flag_for_asset(self):
        self.asset.criticality = "critical"
        self.asset.save(update_fields=["criticality", "updated_at"])
        self.client.post(
            reverse("ai-agent-manual-run"),
            {"agent_slug": "maintenance-agent", "company": self.company.id, "site": self.site.id},
            format="json",
        )

        self.assertTrue(
            AgentAssetAttentionFlag.objects.filter(
                agent__slug="maintenance-agent",
                company=self.company,
                asset=self.asset,
            ).exists()
        )

    def test_profitability_agent_detects_client_negative_margin(self):
        contract = MaintenanceContractFactory(
            company=self.company,
            client=self.maintenance_client,
            operational_site=self.site,
            contract_number="MCT-AI-001",
            contract_value=Decimal("500.00"),
        )
        order = ServiceOrderFactory(
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            maintenance_contract=contract,
            assigned_to=self.user,
            created_by=self.user,
            status=ServiceOrder.Status.COMPLETED,
        )
        WorkLogFactory(service_order=order, user=self.user, labor_minutes=480)
        StockMovementFactory(
            company=self.company,
            operational_site=self.site,
            service_order=order,
            part=PartFactory(company=self.company, operational_site=self.site, unit_cost=400),
            quantity=1,
        )
        ScheduledVisitFactory(
            company=self.company,
            operational_site=self.site,
            work_order=order,
            asset=self.asset,
            technician=self.user,
            estimated_travel_minutes=240,
        )

        response = self.client.post(
            reverse("ai-agent-profitability-run"),
            {"company": self.company.id, "client_public_id": str(self.maintenance_client.public_id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="profitability-agent",
                recommendation_type="client_margin_alert",
                entity_id=str(self.maintenance_client.public_id),
            ).exists()
        )

    def test_profitability_agent_detects_contract_deficit(self):
        contract = MaintenanceContractFactory(
            company=self.company,
            client=self.maintenance_client,
            operational_site=self.site,
            contract_number="MCT-AI-002",
            contract_value=Decimal("600.00"),
        )
        order = ServiceOrderFactory(
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            maintenance_contract=contract,
            assigned_to=self.user,
            created_by=self.user,
        )
        WorkLogFactory(service_order=order, user=self.user, labor_minutes=600)
        StockMovementFactory(
            company=self.company,
            operational_site=self.site,
            service_order=order,
            part=PartFactory(company=self.company, operational_site=self.site, unit_cost=350),
            quantity=2,
        )

        response = self.client.post(
            reverse("ai-agent-profitability-run"),
            {"company": self.company.id, "contract_public_id": str(contract.public_id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="profitability-agent",
                recommendation_type="contract_profitability_risk",
                entity_id=str(contract.public_id),
            ).exists()
        )

    def test_profitability_agent_detects_excessive_service_cost(self):
        contract = MaintenanceContractFactory(company=self.company, client=self.maintenance_client, operational_site=self.site, contract_value=Decimal("2000.00"))
        order = ServiceOrderFactory(
            order_number="OS-PROFIT-001",
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            maintenance_contract=contract,
            assigned_to=self.user,
            created_by=self.user,
        )
        ServiceQuoteFactory(company=self.company, operational_site=self.site, work_order=order, asset=self.asset, total_value=Decimal("250.00"))
        WorkLogFactory(service_order=order, user=self.user, labor_minutes=300)
        StockMovementFactory(
            company=self.company,
            operational_site=self.site,
            service_order=order,
            part=PartFactory(company=self.company, operational_site=self.site, unit_cost=500),
            quantity=1,
        )

        response = self.client.post(
            reverse("ai-agent-profitability-run"),
            {"company": self.company.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="profitability-agent",
                recommendation_type="excessive_service_cost",
                entity_id=str(order.public_id),
            ).exists()
        )

    def test_profitability_agent_detects_route_margin_erosion(self):
        contract = MaintenanceContractFactory(company=self.company, client=self.maintenance_client, operational_site=self.site, contract_value=Decimal("500.00"))
        order = ServiceOrderFactory(
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            maintenance_contract=contract,
            assigned_to=self.user,
            created_by=self.user,
        )
        WorkLogFactory(service_order=order, user=self.user, labor_minutes=60)
        ScheduledVisitFactory(
            company=self.company,
            operational_site=self.site,
            work_order=order,
            asset=self.asset,
            technician=self.user,
            estimated_travel_minutes=360,
        )

        response = self.client.post(
            reverse("ai-agent-profitability-run"),
            {"company": self.company.id, "site": self.site.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="profitability-agent",
                recommendation_type="route_margin_erosion",
            ).exists()
        )

    def test_profitability_agent_suggests_commercial_review(self):
        contract = MaintenanceContractFactory(company=self.company, client=self.maintenance_client, operational_site=self.site, contract_value=Decimal("500.00"))
        order = ServiceOrderFactory(
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            maintenance_contract=contract,
            assigned_to=self.user,
            created_by=self.user,
        )
        WorkLogFactory(service_order=order, user=self.user, labor_minutes=420)
        StockMovementFactory(
            company=self.company,
            operational_site=self.site,
            service_order=order,
            part=PartFactory(company=self.company, operational_site=self.site, unit_cost=320),
            quantity=2,
        )

        self.client.post(
            reverse("ai-agent-profitability-run"),
            {"company": self.company.id, "contract_public_id": str(contract.public_id)},
            format="json",
        )

        self.assertTrue(
            AgentActionProposal.objects.filter(
                agent_run__agent__slug="profitability-agent",
                action_type="suggest_contract_repricing",
                target_entity_id=str(contract.public_id),
            ).exists()
        )

    def test_profitability_health_endpoint_respects_scope(self):
        contract = MaintenanceContractFactory(company=self.company, client=self.maintenance_client, operational_site=self.site, contract_value=Decimal("500.00"))
        order = ServiceOrderFactory(
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            maintenance_contract=contract,
            assigned_to=self.user,
            created_by=self.user,
        )
        WorkLogFactory(service_order=order, user=self.user, labor_minutes=420)
        self.client.post(reverse("ai-agent-profitability-run"), {"company": self.company.id}, format="json")

        response = self.client.get(reverse("ai-agent-profitability-health-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(_payload_items(response)), 1)
        self.assertTrue(AgentProfitabilityAttentionFlag.objects.filter(agent__slug="profitability-agent", company=self.company).exists())

    def test_marketplace_agent_identifies_best_viable_candidate(self):
        skill = TechnicianSkillFactory(name="hvac")
        request = TechnicianServiceRequestFactory(
            requester_company=self.company,
            related_client=self.maintenance_client,
            related_site=self.site,
            related_asset=self.asset,
            city="Sao Paulo",
            state="SP",
            category="hvac",
            priority="high",
        )
        region = ServiceRegionFactory(city="Sao Paulo", state="SP")
        TechnicianSkillAssignmentFactory(technician_profile=self.primary_profile, skill=skill)
        TechnicianServiceRegionFactory(technician_profile=self.primary_profile, service_region=region)
        TechnicianAvailabilityFactory(technician_profile=self.primary_profile, weekday=request.requested_date.date().isoweekday())
        TechnicianMatchingRecordFactory(
            technician_service_request=request,
            technician_profile=self.primary_profile,
            match_score=Decimal("91.00"),
            ranking_position=1,
            distance_km=Decimal("8.00"),
        )

        response = self.client.post(
            reverse("ai-agent-marketplace-run"),
            {"company": self.company.id, "service_request_public_id": str(request.public_id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="marketplace-agent",
                recommendation_type="technician_allocation_recommendation",
                entity_id=str(request.public_id),
            ).exists()
        )

    def test_marketplace_agent_detects_unavailable_top_theoretical_candidate(self):
        skill = TechnicianSkillFactory(name="climatizacao")
        request = TechnicianServiceRequestFactory(
            requester_company=self.company,
            related_client=self.maintenance_client,
            related_site=self.site,
            related_asset=self.asset,
            city="Sao Paulo",
            state="SP",
            category="climatizacao",
            priority="urgent",
        )
        region = ServiceRegionFactory(city="Sao Paulo", state="SP")
        TechnicianSkillAssignmentFactory(technician_profile=self.primary_profile, skill=skill)
        TechnicianSkillAssignmentFactory(technician_profile=self.secondary_profile, skill=skill)
        TechnicianServiceRegionFactory(technician_profile=self.primary_profile, service_region=region)
        TechnicianServiceRegionFactory(technician_profile=self.secondary_profile, service_region=region)
        TechnicianAvailabilityFactory(technician_profile=self.secondary_profile, weekday=request.requested_date.date().isoweekday())
        self.primary_profile.marketplace_status = self.primary_profile.MarketplaceStatus.BUSY
        self.primary_profile.save(update_fields=["marketplace_status", "updated_at"])
        for index in range(6):
            ScheduledVisitFactory(
                company=self.company,
                operational_site=self.site,
                technician=self.user,
                scheduled_date=request.requested_date.date(),
                estimated_duration_minutes=120,
                estimated_travel_minutes=30,
                route_order=index + 1,
            )
        TechnicianMatchingRecordFactory(
            technician_service_request=request,
            technician_profile=self.primary_profile,
            match_score=Decimal("95.00"),
            ranking_position=1,
            distance_km=Decimal("10.00"),
        )
        TechnicianMatchingRecordFactory(
            technician_service_request=request,
            technician_profile=self.secondary_profile,
            match_score=Decimal("86.00"),
            ranking_position=2,
            distance_km=Decimal("15.00"),
        )

        response = self.client.post(
            reverse("ai-agent-marketplace-run"),
            {"company": self.company.id, "service_request_public_id": str(request.public_id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="marketplace-agent",
                recommendation_type="technician_unavailable_conflict",
                entity_id=str(request.public_id),
            ).exists()
        )

    def test_marketplace_agent_detects_request_without_viable_candidate(self):
        request = TechnicianServiceRequestFactory(
            requester_company=self.company,
            related_client=self.maintenance_client,
            related_site=self.site,
            related_asset=self.asset,
            city="Curitiba",
            state="PR",
            category="inversores",
            priority="urgent",
        )
        TechnicianMatchingRecordFactory(
            technician_service_request=request,
            technician_profile=self.primary_profile,
            match_score=Decimal("89.00"),
            ranking_position=1,
            distance_km=Decimal("180.00"),
        )

        response = self.client.post(
            reverse("ai-agent-marketplace-run"),
            {"company": self.company.id, "service_request_public_id": str(request.public_id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="marketplace-agent",
                recommendation_type="no_viable_candidate_alert",
                entity_id=str(request.public_id),
            ).exists()
        )

    def test_marketplace_agent_suggests_fallback_when_appropriate(self):
        request = TechnicianServiceRequestFactory(
            requester_company=self.company,
            related_client=self.maintenance_client,
            related_site=self.site,
            related_asset=self.asset,
            city="Rio de Janeiro",
            state="RJ",
            category="hvac",
            priority="urgent",
        )
        TechnicianMatchingRecordFactory(
            technician_service_request=request,
            technician_profile=self.primary_profile,
            match_score=Decimal("88.00"),
            ranking_position=1,
            distance_km=Decimal("220.00"),
        )

        self.client.post(
            reverse("ai-agent-marketplace-run"),
            {"company": self.company.id, "service_request_public_id": str(request.public_id)},
            format="json",
        )

        self.assertTrue(
            AgentActionProposal.objects.filter(
                agent_run__agent__slug="marketplace-agent",
                action_type="activate_marketplace_fallback",
                target_entity_id=str(request.public_id),
            ).exists()
        )

    def test_marketplace_agent_considers_sla_and_distance(self):
        request = TechnicianServiceRequestFactory(
            requester_company=self.company,
            related_client=self.maintenance_client,
            related_site=self.site,
            related_asset=self.asset,
            city="Sao Paulo",
            state="SP",
            category="hvac",
            priority="urgent",
            deadline_at=timezone.now() + timedelta(hours=2),
        )
        region = ServiceRegionFactory(city="Sao Paulo", state="SP")
        TechnicianServiceRegionFactory(technician_profile=self.secondary_profile, service_region=region)
        TechnicianAvailabilityFactory(technician_profile=self.secondary_profile, weekday=request.requested_date.date().isoweekday())
        TechnicianMatchingRecordFactory(
            technician_service_request=request,
            technician_profile=self.secondary_profile,
            match_score=Decimal("83.00"),
            ranking_position=1,
            distance_km=Decimal("18.00"),
        )

        response = self.client.post(
            reverse("ai-agent-marketplace-run"),
            {"company": self.company.id, "service_request_public_id": str(request.public_id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="marketplace-agent",
                recommendation_type="sla_allocation_risk",
                entity_id=str(request.public_id),
            ).exists()
        )

    def test_marketplace_health_endpoint_respects_scope(self):
        request = TechnicianServiceRequestFactory(
            requester_company=self.company,
            related_client=self.maintenance_client,
            related_site=self.site,
            related_asset=self.asset,
            city="Sao Paulo",
            state="SP",
            category="hvac",
        )
        region = ServiceRegionFactory(city="Sao Paulo", state="SP")
        TechnicianServiceRegionFactory(technician_profile=self.primary_profile, service_region=region)
        TechnicianAvailabilityFactory(technician_profile=self.primary_profile, weekday=request.requested_date.date().isoweekday())
        TechnicianMatchingRecordFactory(
            technician_service_request=request,
            technician_profile=self.primary_profile,
            match_score=Decimal("90.00"),
            ranking_position=1,
            distance_km=Decimal("10.00"),
        )
        self.client.post(reverse("ai-agent-marketplace-run"), {"company": self.company.id, "service_request_public_id": str(request.public_id)}, format="json")

        response = self.client.get(reverse("ai-agent-marketplace-health-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(_payload_items(response)), 1)
        self.assertTrue(AgentMarketplaceRequestFlag.objects.filter(agent__slug="marketplace-agent", company=self.company).exists())

    def test_anomaly_agent_detects_abnormal_failure_spike(self):
        for offset in (1, 2, 3, 4):
            FailureEvent.objects.create(
                asset=self.asset,
                service_order=self.order,
                symptom=f"Falha anomala {offset}",
                probable_cause="Spike",
                severity="high",
                detected_at=timezone.now() - timedelta(days=offset),
            )

        response = self.client.post(
            reverse("ai-agent-anomaly-run"),
            {"company": self.company.id, "asset_public_id": str(self.asset.public_id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="anomaly-agent",
                recommendation_type="anomaly_failure_spike",
                entity_id=str(self.asset.public_id),
            ).exists()
        )

    def test_anomaly_agent_detects_backlog_outside_pattern(self):
        for index in range(8):
            ServiceOrderFactory(
                client=self.maintenance_client,
                operational_site=self.site,
                asset=self.asset,
                assigned_to=self.user,
                created_by=self.user,
                maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
                status=ServiceOrder.Status.OPEN,
                opened_at=timezone.now() - timedelta(days=1),
                title=f"Backlog {index}",
            )
        ServiceOrderFactory(
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            assigned_to=self.user,
            created_by=self.user,
            maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
            status=ServiceOrder.Status.OPEN,
            opened_at=timezone.now() - timedelta(days=20),
            title="Baseline backlog",
        )

        response = self.client.post(
            reverse("ai-agent-anomaly-run"),
            {"company": self.company.id, "site": self.site.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="anomaly-agent",
                recommendation_type="anomaly_backlog_growth",
                entity_id=str(self.site.public_id),
            ).exists()
        )

    def test_anomaly_agent_detects_sla_drop(self):
        for offset in (20, 19, 18, 17):
            opened_at = timezone.now() - timedelta(days=offset)
            ServiceOrderFactory(
                client=self.maintenance_client,
                operational_site=self.site,
                asset=self.asset,
                assigned_to=self.user,
                created_by=self.user,
                maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
                status=ServiceOrder.Status.COMPLETED,
                priority=ServiceOrder.Priority.HIGH,
                opened_at=opened_at,
                started_at=opened_at + timedelta(minutes=30),
                completed_at=opened_at + timedelta(hours=2),
                title=f"SLA ok {offset}",
            )
        for offset in (3, 2, 1):
            opened_at = timezone.now() - timedelta(days=offset)
            ServiceOrderFactory(
                client=self.maintenance_client,
                operational_site=self.site,
                asset=self.asset,
                assigned_to=self.user,
                created_by=self.user,
                maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
                status=ServiceOrder.Status.COMPLETED,
                priority=ServiceOrder.Priority.HIGH,
                opened_at=opened_at,
                started_at=opened_at + timedelta(hours=8),
                completed_at=opened_at + timedelta(hours=10),
                title=f"SLA ruim {offset}",
            )

        response = self.client.post(
            reverse("ai-agent-anomaly-run"),
            {"company": self.company.id, "site": self.site.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="anomaly-agent",
                recommendation_type="anomaly_sla_drop",
                entity_id=str(self.site.public_id),
            ).exists()
        )

    def test_anomaly_agent_detects_parts_consumption_outside_pattern(self):
        part = PartFactory(company=self.company, operational_site=self.site, code="PRT-ANOM-01", unit_cost=Decimal("150.00"))
        StockMovementFactory(
            company=self.company,
            operational_site=self.site,
            service_order=self.order,
            part=part,
            quantity=Decimal("1.00"),
            occurred_at=timezone.now() - timedelta(days=18),
        )
        for offset in (1, 2, 3):
            StockMovementFactory(
                company=self.company,
                operational_site=self.site,
                service_order=self.order,
                part=part,
                quantity=Decimal("3.00"),
                occurred_at=timezone.now() - timedelta(days=offset),
            )

        response = self.client.post(
            reverse("ai-agent-anomaly-run"),
            {"company": self.company.id, "part_public_id": str(part.public_id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="anomaly-agent",
                recommendation_type="anomaly_parts_consumption",
                entity_id=str(part.public_id),
            ).exists()
        )

    def test_anomaly_agent_detects_contract_margin_shift(self):
        contract = MaintenanceContractFactory(
            company=self.company,
            client=self.maintenance_client,
            operational_site=self.site,
            contract_number="MCT-ANOM-001",
            contract_value=Decimal("2000.00"),
        )
        current_period = ExecutiveAnalyticsService.get_period(reference_date=timezone.localdate(), period_type=OperationalMetrics.PeriodType.MONTHLY)
        previous_period = ExecutiveAnalyticsService.get_period(reference_date=current_period.start - timedelta(days=1), period_type=OperationalMetrics.PeriodType.MONTHLY)
        order = ServiceOrderFactory(
            client=self.maintenance_client,
            operational_site=self.site,
            asset=self.asset,
            maintenance_contract=contract,
            assigned_to=self.user,
            created_by=self.user,
            status=ServiceOrder.Status.COMPLETED,
        )
        WorkLogFactory(service_order=order, user=self.user, labor_minutes=600)
        StockMovementFactory(
            company=self.company,
            operational_site=self.site,
            service_order=order,
            part=PartFactory(company=self.company, operational_site=self.site, unit_cost=500),
            quantity=2,
        )
        ContractProfitability.objects.create(
            company=self.company,
            contract=contract,
            period_type=previous_period.period_type,
            period_start=previous_period.start,
            period_end=previous_period.end,
            revenue=Decimal("2000.00"),
            cost=Decimal("1400.00"),
            profit=Decimal("600.00"),
            margin=Decimal("30.00"),
        )

        response = self.client.post(
            reverse("ai-agent-anomaly-run"),
            {"company": self.company.id, "contract_public_id": str(contract.public_id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="anomaly-agent",
                recommendation_type="anomaly_contract_margin_shift",
                entity_id=str(contract.public_id),
            ).exists()
        )

    def test_anomaly_health_endpoint_respects_scope(self):
        for offset in (1, 2, 3, 4):
            FailureEvent.objects.create(
                asset=self.asset,
                service_order=self.order,
                symptom=f"Falha health {offset}",
                probable_cause="Health",
                severity="high",
                detected_at=timezone.now() - timedelta(days=offset),
            )
        self.client.post(
            reverse("ai-agent-anomaly-run"),
            {"company": self.company.id, "asset_public_id": str(self.asset.public_id)},
            format="json",
        )

        response = self.client.get(reverse("ai-agent-anomaly-health-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(_payload_items(response)), 1)
        self.assertTrue(AgentAnomalyAttentionFlag.objects.filter(agent__slug="anomaly-agent", company=self.company).exists())

    def test_proposal_approval_changes_status(self):
        AgentRun.objects.all().delete()
        self.client.post(
            reverse("ai-agent-manual-run"),
            {"agent_slug": "maintenance-agent", "company": self.company.id, "site": self.site.id},
            format="json",
        )
        proposal = AgentActionProposal.objects.filter(agent_run__company=self.company).latest("created_at")

        response = self.client.post(
            reverse("ai-agent-action-proposals-approve", kwargs={"pk": proposal.pk}),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, AgentActionProposal.Status.APPROVED)

    def test_anomaly_proposal_approval_changes_status(self):
        for offset in (1, 2, 3, 4):
            FailureEvent.objects.create(
                asset=self.asset,
                service_order=self.order,
                symptom=f"Falha approve {offset}",
                probable_cause="Approval",
                severity="high",
                detected_at=timezone.now() - timedelta(days=offset),
            )
        self.client.post(
            reverse("ai-agent-anomaly-run"),
            {"company": self.company.id, "asset_public_id": str(self.asset.public_id)},
            format="json",
        )
        proposal = AgentActionProposal.objects.filter(agent_run__agent__slug="anomaly-agent").latest("created_at")

        response = self.client.post(
            reverse("ai-agent-action-proposals-approve", kwargs={"pk": proposal.pk}),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, AgentActionProposal.Status.APPROVED)

    def test_maintenance_run_endpoint_accepts_asset_focus(self):
        response = self.client.post(
            reverse("ai-agent-maintenance-run"),
            {"company": self.company.id, "site": self.site.id, "asset_public_id": str(self.asset.public_id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["trigger_reference"], f"asset:{self.asset.public_id}")

    def test_recommendations_are_scoped_by_company_membership(self):
        self.client.post(
            reverse("ai-agent-manual-run"),
            {"agent_slug": "maintenance-agent", "company": self.company.id, "site": self.site.id},
            format="json",
        )
        outsider = UserFactory(email="outsider-ai@smart360.local", password="StrongPass123")
        foreign_company = CompanyFactory(name="Foreign AI", slug="foreign-ai")
        MembershipFactory(user=outsider, company=foreign_company, is_primary=True)
        assign_smart_system_role(outsider, "maintenance-manager", company=foreign_company)
        self.client.force_authenticate(outsider)

        response = self.client.get(reverse("ai-agent-recommendations-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(_payload_items(response)), 0)

    def test_anomaly_recommendations_are_scoped_by_company_membership(self):
        for offset in (1, 2, 3, 4):
            FailureEvent.objects.create(
                asset=self.asset,
                service_order=self.order,
                symptom=f"Falha scope {offset}",
                probable_cause="Scope",
                severity="high",
                detected_at=timezone.now() - timedelta(days=offset),
            )
        self.client.post(
            reverse("ai-agent-anomaly-run"),
            {"company": self.company.id, "asset_public_id": str(self.asset.public_id)},
            format="json",
        )
        outsider = UserFactory(email="outsider-anomaly@smart360.local", password="StrongPass123")
        foreign_company = CompanyFactory(name="Foreign Anomaly", slug="foreign-anomaly")
        MembershipFactory(user=outsider, company=foreign_company, is_primary=True)
        assign_smart_system_role(outsider, "maintenance-manager", company=foreign_company)
        self.client.force_authenticate(outsider)

        response = self.client.get(reverse("ai-agent-anomaly-health-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(_payload_items(response)), 0)

    def test_attention_assets_endpoint_respects_scope(self):
        self.client.post(
            reverse("ai-agent-manual-run"),
            {"agent_slug": "maintenance-agent", "company": self.company.id, "site": self.site.id},
            format="json",
        )
        response = self.client.get(reverse("ai-agent-maintenance-attention-assets-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(_payload_items(response)), 1)

    def test_scheduling_agent_detects_technician_overload(self):
        target_date = timezone.localdate() + timedelta(days=1)
        TechnicianScheduleFactory(company=self.company, operational_site=self.site, technician=self.user, date=target_date)
        TechnicianScheduleFactory(company=self.company, operational_site=self.site, technician=self.secondary_technician, date=target_date)
        for index in range(6):
            ScheduledVisitFactory(
                company=self.company,
                operational_site=self.site,
                technician=self.user,
                scheduled_date=target_date,
                estimated_duration_minutes=120,
                estimated_travel_minutes=25,
                route_order=index + 1,
                city="Sao Paulo",
                state="SP",
            )

        response = self.client.post(
            reverse("ai-agent-scheduling-run"),
            {"company": self.company.id, "site": self.site.id, "date": target_date.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="scheduling-agent",
                recommendation_type="technician_overload",
                entity_id=str(self.user.id),
            ).exists()
        )

    def test_scheduling_agent_detects_conflict(self):
        target_date = timezone.localdate() + timedelta(days=2)
        base_start = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=2)
        TechnicianScheduleFactory(company=self.company, operational_site=self.site, technician=self.user, date=target_date)
        ScheduledVisitFactory(
            company=self.company,
            operational_site=self.site,
            technician=self.user,
            scheduled_date=target_date,
            scheduled_start=base_start,
            scheduled_end=base_start + timedelta(minutes=120),
            estimated_duration_minutes=120,
            route_order=1,
            conflict_flags=["overlap"],
        )
        ScheduledVisitFactory(
            company=self.company,
            operational_site=self.site,
            technician=self.user,
            scheduled_date=target_date,
            scheduled_start=base_start + timedelta(minutes=60),
            scheduled_end=base_start + timedelta(minutes=180),
            estimated_duration_minutes=120,
            route_order=2,
            conflict_flags=["overlap"],
        )

        response = self.client.post(
            reverse("ai-agent-scheduling-run"),
            {"company": self.company.id, "site": self.site.id, "date": target_date.isoformat(), "technician_id": self.user.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="scheduling-agent",
                entity_id=str(self.user.id),
                title__icontains="Conflitos detectados",
            ).exists()
        )

    def test_scheduling_agent_detects_unassigned_critical_visit(self):
        target_date = timezone.localdate() + timedelta(days=3)
        ScheduledVisitFactory(
            company=self.company,
            operational_site=self.site,
            technician=None,
            technician_schedule=None,
            route_plan=None,
            scheduled_date=target_date,
            priority="urgent",
            status="pending_assignment",
            title="OS Critica sem tecnico",
            city="Sao Paulo",
            state="SP",
        )

        response = self.client.post(
            reverse("ai-agent-scheduling-run"),
            {"company": self.company.id, "site": self.site.id, "date": target_date.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="scheduling-agent",
                recommendation_type="unassigned_visit_attention",
            ).exists()
        )

    def test_scheduling_agent_suggests_route_reorder(self):
        target_date = timezone.localdate() + timedelta(days=4)
        base_start = timezone.now().replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=4)
        TechnicianScheduleFactory(company=self.company, operational_site=self.site, technician=self.user, date=target_date)
        ScheduledVisitFactory(
            company=self.company,
            operational_site=self.site,
            technician=self.user,
            scheduled_date=target_date,
            route_order=1,
            city="Sao Paulo",
            state="SP",
            scheduled_start=base_start,
            scheduled_end=base_start + timedelta(minutes=60),
        )
        ScheduledVisitFactory(
            company=self.company,
            operational_site=self.site,
            technician=self.user,
            scheduled_date=target_date,
            route_order=2,
            city="Rio de Janeiro",
            state="RJ",
            scheduled_start=base_start + timedelta(minutes=90),
            scheduled_end=base_start + timedelta(minutes=150),
        )
        ScheduledVisitFactory(
            company=self.company,
            operational_site=self.site,
            technician=self.user,
            scheduled_date=target_date,
            route_order=3,
            city="Sao Paulo",
            state="SP",
            scheduled_start=base_start + timedelta(minutes=180),
            scheduled_end=base_start + timedelta(minutes=240),
        )

        response = self.client.post(
            reverse("ai-agent-scheduling-run"),
            {"company": self.company.id, "site": self.site.id, "date": target_date.isoformat(), "technician_id": self.user.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentRecommendation.objects.filter(
                agent_run__agent__slug="scheduling-agent",
                recommendation_type="route_reorder",
            ).exists()
        )

    def test_scheduling_agent_suggests_redistribution(self):
        target_date = timezone.localdate() + timedelta(days=5)
        TechnicianScheduleFactory(company=self.company, operational_site=self.site, technician=self.user, date=target_date)
        TechnicianScheduleFactory(company=self.company, operational_site=self.site, technician=self.secondary_technician, date=target_date)
        for index in range(6):
            ScheduledVisitFactory(
                company=self.company,
                operational_site=self.site,
                technician=self.user,
                scheduled_date=target_date,
                estimated_duration_minutes=110,
                estimated_travel_minutes=25,
                route_order=index + 1,
                city="Sao Paulo",
                state="SP",
            )
        ScheduledVisitFactory(
            company=self.company,
            operational_site=self.site,
            technician=self.secondary_technician,
            scheduled_date=target_date,
            estimated_duration_minutes=60,
            estimated_travel_minutes=10,
            route_order=1,
            city="Sao Paulo",
            state="SP",
        )

        response = self.client.post(
            reverse("ai-agent-scheduling-run"),
            {"company": self.company.id, "site": self.site.id, "date": target_date.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AgentActionProposal.objects.filter(
                agent_run__agent__slug="scheduling-agent",
                action_type="reassign_visits_between_technicians",
            ).exists()
        )

    def test_scheduling_health_endpoint_respects_scope(self):
        target_date = timezone.localdate() + timedelta(days=6)
        TechnicianScheduleFactory(company=self.company, operational_site=self.site, technician=self.user, date=target_date)
        for index in range(6):
            ScheduledVisitFactory(
                company=self.company,
                operational_site=self.site,
                technician=self.user,
                scheduled_date=target_date,
                estimated_duration_minutes=120,
                estimated_travel_minutes=30,
                route_order=index + 1,
                city="Sao Paulo",
                state="SP",
            )
        self.client.post(
            reverse("ai-agent-scheduling-run"),
            {"company": self.company.id, "site": self.site.id, "date": target_date.isoformat()},
            format="json",
        )

        response = self.client.get(reverse("ai-agent-scheduling-health-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, list):
            self.assertGreaterEqual(len(response.data), 1)
            results = response.data
        else:
            self.assertGreaterEqual(len(_payload_items(response)), 1)
            results = response.data.get("results", [])

        self.assertTrue(results)

    def test_manager_copilot_query_respects_scope(self):
        other_company = CompanyFactory(name="Outra Empresa", slug="outra-empresa")
        other_client = MaintenanceClientFactory(company=other_company, display_name="Cliente Externo")
        other_site = OperationalSiteFactory(maintenance_client=other_client, name="Unidade Externa", code="EXT-01")
        other_agent = AgentRegistryService.get_agent_definition("anomaly-agent")
        other_run = AgentRun.objects.create(
            agent=other_agent,
            trigger_type=AgentRun.TriggerType.MANUAL,
            company=other_company,
            site=other_site,
            status=AgentRun.Status.COMPLETED,
        )
        AgentRecommendation.objects.create(
            agent_run=other_run,
            company=other_company,
            site=other_site,
            recommendation_type="anomaly_site_risk_alert",
            title="Anomalia externa",
            summary="Nao deveria aparecer para este usuario.",
            severity="critical",
            priority="immediate",
            entity_type="site",
            entity_id=str(other_site.public_id),
        )

        response = self.client.post(
            reverse("ai-agent-copilot-query"),
            {"query": "Quais sao os maiores riscos operacionais hoje?", "company": self.company.id, "site": self.site.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        recommendation_titles = [item["title"] for item in response.data["response"]["recommendation_cards"]]
        self.assertNotIn("Anomalia externa", recommendation_titles)

    def test_manager_copilot_aggregates_recommendations_and_pending_proposals(self):
        self.client.post(
            reverse("ai-agent-manual-run"),
            {"agent_slug": "maintenance-agent", "company": self.company.id, "site": self.site.id},
            format="json",
        )

        response = self.client.post(
            reverse("ai-agent-copilot-query"),
            {"query": "Quais recomendacoes pendentes eu deveria olhar primeiro?", "company": self.company.id, "site": self.site.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data["response"]["recommendation_cards"]), 1)
        self.assertGreaterEqual(len(response.data["response"]["proposal_cards"]), 1)

    def test_manager_copilot_keeps_basic_session_context(self):
        first_response = self.client.post(
            reverse("ai-agent-copilot-query"),
            {"query": "Resuma a situacao da unidade Unidade AI nesta semana.", "company": self.company.id, "site": self.site.id},
            format="json",
        )
        session_public_id = first_response.data["session"]["public_id"]

        second_response = self.client.post(
            reverse("ai-agent-copilot-query"),
            {"query": "E comparado com semana passada?", "session_public_id": session_public_id, "company": self.company.id, "site": self.site.id},
            format="json",
        )

        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.data["context"]["site_name"], self.site.name)
        self.assertEqual(second_response.data["context"]["intent"], "comparison")

    def test_manager_copilot_classifies_profitability_intent(self):
        response = self.client.post(
            reverse("ai-agent-copilot-query"),
            {"query": "Tem algum contrato dando prejuizo?", "company": self.company.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["context"]["intent"], "profitability")

    def test_manager_copilot_approval_endpoint_updates_status(self):
        self.client.post(
            reverse("ai-agent-manual-run"),
            {"agent_slug": "maintenance-agent", "company": self.company.id, "site": self.site.id},
            format="json",
        )
        proposal = AgentActionProposal.objects.filter(agent_run__agent__slug="maintenance-agent").latest("created_at")

        response = self.client.post(reverse("ai-agent-copilot-proposal-approve", kwargs={"proposal_public_id": proposal.public_id}), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        proposal.refresh_from_db()
        self.assertEqual(proposal.status, AgentActionProposal.Status.APPROVED)

    def test_manager_copilot_reject_endpoint_respects_permissions(self):
        outsider = UserFactory(email="outsider@smart360.local", password="StrongPass123")
        self.client.post(
            reverse("ai-agent-manual-run"),
            {"agent_slug": "maintenance-agent", "company": self.company.id, "site": self.site.id},
            format="json",
        )
        proposal = AgentActionProposal.objects.filter(agent_run__agent__slug="maintenance-agent").latest("created_at")

        self.client.force_authenticate(outsider)
        response = self.client.post(
            reverse("ai-agent-copilot-proposal-reject", kwargs={"proposal_public_id": proposal.public_id}),
            {"reason": "sem permissao"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_copilot_creates_session_and_messages(self):
        response = self.client.post(
            reverse("ai-agent-copilot-query"),
            {"query": "Quais sao os maiores riscos operacionais hoje?", "company": self.company.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session_public_id = response.data["session"]["public_id"]
        self.assertTrue(ManagerCopilotSession.objects.filter(public_id=session_public_id).exists())
        self.assertEqual(ManagerCopilotMessage.objects.filter(session__public_id=session_public_id).count(), 2)

    def test_manager_copilot_persists_decimal_payload_as_json(self):
        period = ExecutiveAnalyticsService.get_period(reference_date=timezone.localdate(), period_type=OperationalMetrics.PeriodType.MONTHLY)
        OperationalMetrics.objects.create(
            company=self.company,
            period_type=period.period_type,
            period_start=period.start,
            period_end=period.end,
            total_work_orders=4,
            total_revenue=Decimal("1234.56"),
            total_cost=Decimal("789.10"),
            total_profit=Decimal("445.46"),
            sla_compliance_rate=Decimal("97.50"),
            avg_response_time=Decimal("2.25"),
        )

        response = self.client.post(
            reverse("ai-agent-copilot-query"),
            {"query": "Quais sao os maiores riscos operacionais hoje?", "company": self.company.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        message = ManagerCopilotMessage.objects.filter(role=ManagerCopilotMessage.Role.ASSISTANT).latest("created_at")
        json.dumps(message.structured_payload)

        def contains_decimal(value):
            if isinstance(value, Decimal):
                return True
            if isinstance(value, dict):
                return any(contains_decimal(item) for item in value.values())
            if isinstance(value, list):
                return any(contains_decimal(item) for item in value)
            return False

        self.assertFalse(contains_decimal(message.structured_payload))

    def test_manager_copilot_generates_observability_logs(self):
        self.client.post(
            reverse("ai-agent-copilot-query"),
            {"query": "Mostre os principais desvios anomalos recentes.", "company": self.company.id},
            format="json",
        )

        self.assertTrue(SystemEventLog.objects.filter(event_type="copilot.manager.query.received").exists())
        self.assertTrue(SystemEventLog.objects.filter(event_type="copilot.manager.response.generated").exists())
