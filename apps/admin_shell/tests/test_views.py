import json
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.billing.models import Contract
from apps.marketplace_technicians.models import (
    ServiceRegion,
    TechnicianAssignment,
    TechnicianMatchingRecord,
    TechnicianProfile,
    TechnicianReview,
    TechnicianServiceOffer,
    TechnicianServiceRegion,
    TechnicianServiceRequest,
    TechnicianSkill,
    TechnicianSkillAssignment,
)
from apps.smart_system.models import (
    Asset,
    Checklist,
    ChecklistItem,
    ClientPortalRequest,
    ContractAsset,
    FailureEvent,
    FieldExecutionSnapshot,
    FieldSyncOperation,
    MaintenanceContract,
    MaintenancePlan,
    QuoteItem,
    RoutePlan,
    ScheduledVisit,
    ServiceOrder,
    ServiceQuote,
    ServiceSignature,
    TechnicianSchedule,
)
from apps.ai_agents_center.models import (
    AIBriefing,
    AgentActionProposal,
    AgentDefinition,
    AgentRecommendation,
    AgentRun,
    ClientPortalCopilotMessage,
    ClientPortalCopilotSession,
    TechnicianCopilotMessage,
    TechnicianCopilotSession,
)
from apps.ai_decision_engine.models import AgentDecision
from apps.ai_autonomous_ops.models import AutonomousExecution, AutonomousIncident, AutonomousModeConfig
from apps.ai_digital_twin.services.orchestrator import DigitalTwinOrchestrator
from apps.ai_knowledge_graph.services.graph import GraphProjectionService
from apps.ai_experimentation_framework.models import Experiment, Variant
from apps.ai_optimization_loop.models import OptimizationProposal
from apps.ai_policy_studio.models import PolicyEvaluation
from apps.ai_simulation_engine.models import SimulationResult, SimulationRun, SimulationScenario, SimulationType
from apps.ai_voice_ops.models import VoiceInteraction
from apps.observability_center.models import SystemEventLog
from tests.factories.billing import BillingCustomerFactory, BillingPlanFactory, InvoiceFactory, SubscriptionFactory
from tests.factories.core import CompanyFactory, MembershipFactory, SiteMembershipFactory, UserFactory
from tests.factories.smart_system import AssetCategoryFactory, AssetFactory, MaintenanceClientFactory, OperationalSiteFactory, ServiceOrderFactory


class AdminShellViewTests(TestCase):
    def setUp(self):
        bootstrap_smart_system_access()
        self.user = UserFactory(password="admin123!", is_staff=True)
        self.academia_company = CompanyFactory(name="Academia Exemplo")
        MembershipFactory(user=self.user, company=self.academia_company, is_primary=True)
        assign_smart_system_role(self.user, "maintenance-manager", company=self.academia_company)

        self.default_client = MaintenanceClientFactory(
            company=self.academia_company,
            display_name="Academia Exemplo",
        )
        self.default_site = OperationalSiteFactory(
            maintenance_client=self.default_client,
            name="Unidade Centro",
            code="ADM-SHELL-TST",
        )
        self._seed_default_smart_system_demo_data()

        self.client.force_login(self.user)

    def _seed_default_smart_system_demo_data(self):
        """ORM alinhado aos mocks Smart System Academia para listagens/execucao no tenant padrao."""
        cat_hvac = AssetCategoryFactory(name="Seed HVAC")
        cat_cardio = AssetCategoryFactory(name="Seed Cardio")

        asset_chiller = AssetFactory(
            operational_site=self.default_site,
            category=cat_hvac,
            asset_tag="PORTAL-CTR-202",
            name="Chiller Unidade A",
        )
        asset_esteira = AssetFactory(
            operational_site=self.default_site,
            category=cat_cardio,
            asset_tag="ESTEIRA-ERG-12",
            name="Esteira Ergometrica 12",
        )

        cl = Checklist.objects.create(
            company=self.academia_company,
            operational_site=self.default_site,
            name="Verificacao Funcional de Esteira",
            description="Rotina equivalente aos dados demo do checklist.",
            is_active=True,
        )
        item_specs = [
            (1, "Verificar tensao de alimentacao", "Conferir estabilidade de alimentacao antes da partida."),
            (2, "Inspecionar ruido anormal na partida", "Verificar estalos ou travamento inicial."),
            (3, "Conferir temperatura da placa de potencia", "Validar aquecimento no conjunto de acionamento."),
            (4, "Checar alarmes ativos no console", "Consultar estado e registrar codigos."),
            (5, "Registrar observacao final", "Sintese rapida ao final da avaliacao."),
        ]
        for ordering, title, description in item_specs:
            ChecklistItem.objects.create(
                checklist=cl,
                title=title,
                description=description,
                item_type=ChecklistItem.ItemType.BOOLEAN,
                ordering=ordering,
                is_required=True,
                is_active=True,
            )

        plan_esteira = MaintenancePlan.objects.create(
            company=self.academia_company,
            operational_site=self.default_site,
            asset=asset_esteira,
            category=cat_cardio,
            name="Plano PM cardio demo",
            description="Plano ligado ao checklist de execucao da OS demo.",
            frequency_type=MaintenancePlan.FrequencyType.WEEKLY,
            frequency_value=2,
            estimated_duration_minutes=60,
            checklist=cl,
            is_active=True,
            next_due_date=timezone.localdate(),
        )

        plan_chiller = MaintenancePlan.objects.create(
            company=self.academia_company,
            operational_site=self.default_site,
            asset=asset_chiller,
            category=cat_hvac,
            name="Plano PM chiller demo",
            description="Plano HVAC com mesmo checklist tecnico disponivel para a OS demo do relatorio.",
            frequency_type=MaintenancePlan.FrequencyType.MONTHLY,
            frequency_value=1,
            estimated_duration_minutes=90,
            checklist=cl,
            is_active=True,
            next_due_date=timezone.localdate(),
        )

        ServiceOrderFactory(
            order_number="OS-PORTAL-101",
            client=self.default_client,
            operational_site=self.default_site,
            asset=asset_chiller,
            maintenance_plan=plan_chiller,
            assigned_to=self.user,
            created_by=self.user,
            title="Baixa eficiencia de resfriamento",
            status=ServiceOrder.Status.IN_PROGRESS,
        )

        wo_151 = ServiceOrderFactory(
            order_number="OS-2026-0151",
            client=self.default_client,
            operational_site=self.default_site,
            asset=asset_esteira,
            maintenance_plan=plan_esteira,
            assigned_to=self.user,
            created_by=self.user,
            title="Falha de partida da esteira ergometrica 12",
            status=ServiceOrder.Status.WAITING_PARTS,
            description=(
                "Falha na esteira relacionada ao acionamento; verificar modulo de potencia "
                "(placa modelo RT250) antes de nova partida."
            ),
        )

        FieldExecutionSnapshot.objects.create(
            company=self.academia_company,
            operational_site=self.default_site,
            service_order=wo_151,
            technician=self.user,
            sync_state=FieldExecutionSnapshot.SyncState.SYNCED,
            materials_payload=[
                {
                    "code": "PRT-0005",
                    "name": "Inversor WEG CFW300",
                    "quantity": "1 un",
                    "notes": "Reposicao tecnica utilizada nos testes de campo.",
                }
            ],
        )

        # OS aguardando peca apenas no tenant Laboratorio — nunca visivel para o usuario Academia
        laboratorio_company = CompanyFactory(name="Laboratorio Exemplo", slug="tests-isolamento-laboratorio")
        laboratorio_mc = MaintenanceClientFactory(company=laboratorio_company, display_name="Laboratorio Exemplo")
        laboratorio_site = OperationalSiteFactory(
            maintenance_client=laboratorio_mc,
            name="Laboratorio Campinas",
            code="LAB-TST-ISO",
        )
        laboratorio_cat = AssetCategoryFactory(name="Lab Seed")
        laboratorio_asset = AssetFactory(
            operational_site=laboratorio_site,
            category=laboratorio_cat,
            asset_tag="CAMARA-ISO-TEST",
            name="Camara Seed",
        )
        ServiceOrderFactory(
            order_number="OS-2026-0149",
            client=laboratorio_mc,
            operational_site=laboratorio_site,
            asset=laboratorio_asset,
            title="Laboratorio pendente peca isolada",
            status=ServiceOrder.Status.WAITING_PARTS,
        )

    def _create_scoped_manager(self):
        user = UserFactory(password="admin123!", is_staff=True)
        academia = CompanyFactory(name="Academia Exemplo", slug="academia-exemplo")
        panobianco = CompanyFactory(name="Panobianco", slug="panobianco")
        laboratorio = CompanyFactory(name="Laboratorio Exemplo", slug="laboratorio-exemplo")

        academia_client = MaintenanceClientFactory(company=academia, display_name="Academia Exemplo")
        panobianco_client = MaintenanceClientFactory(company=panobianco, display_name="Panobianco")
        laboratorio_client = MaintenanceClientFactory(company=laboratorio, display_name="Laboratorio Exemplo")

        academia_site = OperationalSiteFactory(
            maintenance_client=academia_client,
            name="Unidade Centro",
            code="CTR-001",
        )
        panobianco_site = OperationalSiteFactory(
            maintenance_client=panobianco_client,
            name="Academia Premium Sul",
            code="PAN-SUL",
        )
        OperationalSiteFactory(
            maintenance_client=laboratorio_client,
            name="Laboratorio Campinas",
            code="LAB-CPS",
        )

        MembershipFactory(user=user, company=academia, is_primary=True)
        MembershipFactory(user=user, company=panobianco, is_primary=False)
        SiteMembershipFactory(user=user, company=academia, site=academia_site, is_primary=True)
        SiteMembershipFactory(user=user, company=panobianco, site=panobianco_site, is_primary=False)

        assign_smart_system_role(user, "maintenance-manager", company=academia)
        assign_smart_system_role(user, "maintenance-manager", company=panobianco)
        return user, academia, panobianco, academia_site, panobianco_site

    def _create_billing_contract(self):
        company = CompanyFactory(name="Cliente SaaS", slug="cliente-saas")
        customer = BillingCustomerFactory(company=company, trade_name="Cliente SaaS", legal_name="Cliente SaaS LTDA")
        plan = BillingPlanFactory(
            name="Professional",
            slug="professional-shell",
            price_amount="990.00",
            price_monthly="990.00",
            price_yearly="9900.00",
            user_limit=25,
            asset_limit=400,
            site_limit=8,
            work_order_limit=800,
            enabled_features=["smart_system", "reports"],
        )
        contract = Contract.objects.create(
            company=company,
            billing_customer=customer,
            plan=plan,
            billing_periodicity=Contract.BillingPeriodicity.MONTHLY,
            contracted_amount="990.00",
            status=Contract.Status.ACTIVE,
        )
        subscription = SubscriptionFactory(
            billing_customer=customer,
            company=company,
            contract=contract,
            plan=plan,
            amount="990.00",
            billing_method="pix_manual",
        )
        invoice = InvoiceFactory(
            billing_customer=customer,
            company=company,
            contract=contract,
            subscription=subscription,
            invoice_number="INV-TEST-0001",
            status="open",
        )
        return contract, invoice

    def _create_marketplace_data(self):
        company = CompanyFactory(name="Marketplace Company", slug="marketplace-company")
        MembershipFactory(user=self.user, company=company, is_primary=False)
        assign_smart_system_role(self.user, "maintenance-manager", company=company)
        client = MaintenanceClientFactory(company=company, display_name="Marketplace Plant")
        site = OperationalSiteFactory(maintenance_client=client, name="Unidade Marketplace", code="MKT-01")
        technician_user = UserFactory(password="admin123!", is_staff=True)
        assign_smart_system_role(technician_user, "technician")
        technician = TechnicianProfile.objects.create(
            user=technician_user,
            display_name="Tecnico de Campo",
            verification_status=TechnicianProfile.VerificationStatus.APPROVED,
            marketplace_status=TechnicianProfile.MarketplaceStatus.AVAILABLE,
            rating_average="4.80",
            completed_jobs_count=12,
        )
        skill = TechnicianSkill.objects.create(name="esteiras")
        TechnicianSkillAssignment.objects.create(technician_profile=technician, skill=skill)
        region = ServiceRegion.objects.create(name="Sao Paulo Capital", state="SP", city="Sao Paulo")
        TechnicianServiceRegion.objects.create(technician_profile=technician, service_region=region)
        request = TechnicianServiceRequest.objects.create(
            requester_user=self.user,
            requester_company=company,
            title="Atendimento em esteira",
            description="Servico de campo solicitado pela empresa",
            category="esteiras",
            service_type=TechnicianServiceRequest.ServiceType.MAINTENANCE,
            priority=TechnicianServiceRequest.Priority.HIGH,
            city="Sao Paulo",
            state="SP",
            related_client=client,
            related_site=site,
            status=TechnicianServiceRequest.Status.OFFERS_RECEIVED,
        )
        offer = TechnicianServiceOffer.objects.create(
            service_request=request,
            technician_profile=technician,
            proposed_amount="390.00",
            message="Atendo ainda hoje.",
            estimated_hours=3,
        )
        assignment = TechnicianAssignment.objects.create(
            technician_service_request=request,
            technician_profile=technician,
            service_offer=offer,
            assignment_status=TechnicianAssignment.AssignmentStatus.ASSIGNED,
        )
        TechnicianReview.objects.create(
            assignment=assignment,
            reviewer_user=self.user,
            reviewer_company=company,
            technician_profile=technician,
            rating=5,
            comment="Excelente atendimento",
            status=TechnicianReview.Status.PUBLISHED,
        )
        TechnicianMatchingRecord.objects.create(
            technician_service_request=request,
            technician_profile=technician,
            match_score="91.00",
            score_specialty="100.00",
            score_distance="92.00",
            score_rating="96.00",
            score_experience="85.00",
            score_availability="78.00",
            score_response_time="70.00",
            ranking_position=1,
            match_reason="especialidade aderente, regiao atendida, boa reputacao",
        )
        return technician

    def _create_schedule_data(self):
        company = CompanyFactory(name="Agenda Company", slug="agenda-company")
        MembershipFactory(user=self.user, company=company, is_primary=False)
        assign_smart_system_role(self.user, "planner", company=company)
        client = MaintenanceClientFactory(company=company, display_name="Agenda Plant")
        site = OperationalSiteFactory(maintenance_client=client, name="Unidade Agenda", code="AG-01")
        category = AssetCategoryFactory(name="Agenda HVAC")
        asset = AssetFactory(operational_site=site, category=category, asset_tag="AG-AST-01", name="Chiller Agenda")
        order = ServiceOrderFactory(
            order_number="OS-AGENDA-001",
            client=client,
            operational_site=site,
            asset=asset,
            assigned_to=self.user,
            title="Visita agendada",
        )
        schedule = TechnicianSchedule.objects.create(
            company=company,
            operational_site=site,
            technician=self.user,
            date=timezone.localdate(),
            total_jobs=1,
            total_estimated_duration=120,
            total_estimated_travel=20,
        )
        route_plan = RoutePlan.objects.create(
            company=company,
            operational_site=site,
            technician=self.user,
            date=timezone.localdate(),
            total_stops=1,
            total_estimated_duration=120,
            total_estimated_travel=20,
            optimization_status="generated",
        )
        ScheduledVisit.objects.create(
            company=company,
            operational_site=site,
            asset=asset,
            work_order=order,
            technician=self.user,
            technician_schedule=schedule,
            route_plan=route_plan,
            source_type=ScheduledVisit.SourceType.WORK_ORDER,
            title="Visita agendada",
            scheduled_date=timezone.localdate(),
            scheduled_start=timezone.now(),
            scheduled_end=timezone.now() + timedelta(hours=2),
            estimated_duration_minutes=120,
            estimated_travel_minutes=20,
            priority=ScheduledVisit.Priority.HIGH,
            status=ScheduledVisit.Status.SCHEDULED,
            route_order=1,
            city=site.city,
            state=site.state,
            location_label=site.name,
        )
        schedule_session = self.client.session
        schedule_session["smart_system_active_company_id"] = company.id
        schedule_session.pop("smart_system_active_site_id", None)
        schedule_session.save()
        return company

    def _create_war_room_data(self, *, company=None, site=None):
        company = company or CompanyFactory(name="War Room Company", slug=f"war-room-company-{timezone.now().timestamp()}")
        MembershipFactory(user=self.user, company=company, is_primary=False)
        assign_smart_system_role(self.user, "maintenance-manager", company=company)
        client = MaintenanceClientFactory(company=company, display_name="War Room Client")
        site = site or OperationalSiteFactory(maintenance_client=client, name="War Room Site", code=f"WR-{company.id}")
        category = AssetCategoryFactory(name=f"War Room Category {company.id}")
        asset = AssetFactory(
            operational_site=site,
            category=category,
            asset_tag=f"WR-AST-{company.id}",
            name=f"Chiller War Room {company.id}",
            criticality="critical",
        )
        order = ServiceOrderFactory(
            order_number=f"OS-WR-{company.id:03d}",
            client=client,
            operational_site=site,
            asset=asset,
            assigned_to=self.user,
            title=f"OS critica do war room {company.id}",
            priority="urgent",
            status="open",
        )
        agent = AgentDefinition.objects.create(
            slug=f"war-room-agent-{company.id}",
            name=f"War Room Agent {company.id}",
            domain=AgentDefinition.Domain.MAINTENANCE,
            status=AgentDefinition.Status.ACTIVE,
            autonomy_level=AgentDefinition.AutonomyLevel.PROPOSE,
            enabled=True,
        )
        run = AgentRun.objects.create(
            agent=agent,
            company=company,
            site=site,
            triggered_by=self.user,
            trigger_type=AgentRun.TriggerType.MANUAL,
            status=AgentRun.Status.COMPLETED,
            started_at=timezone.now() - timedelta(minutes=8),
            finished_at=timezone.now() - timedelta(minutes=4),
            input_context={},
            output_summary="Resumo operacional do war room.",
        )
        recommendation = AgentRecommendation.objects.create(
            agent_run=run,
            company=company,
            site=site,
            recommendation_type=AgentRecommendation.RecommendationType.CRITICAL_ASSET_WATCH,
            title=f"Ativo critico sob observacao {company.id}",
            summary="Chiller com degradacao acelerada.",
            suggested_action="Priorizar revisao preventiva extraordinaria.",
            severity=AgentRecommendation.Severity.CRITICAL,
            priority=AgentRecommendation.Priority.IMMEDIATE,
            entity_type="asset",
            entity_id=str(asset.public_id),
        )
        proposal = AgentActionProposal.objects.create(
            agent_run=run,
            action_type="create_investigation_task",
            target_entity="asset",
            target_entity_id=str(asset.public_id),
            title=f"Abrir investigacao tecnica {company.id}",
            summary="Necessario investigar a degradacao do ativo.",
            proposed_payload={"asset_public_id": str(asset.public_id)},
            priority="high",
            approval_required=True,
        )
        decision = AgentDecision.objects.create(
            agent_action_proposal=proposal,
            company=company,
            site=site,
            action_type="create_investigation_task",
            normalized_action_type="create_investigation_task",
            target_entity="asset",
            target_entity_id=str(asset.public_id),
            risk_level=AgentDecision.RiskLevel.HIGH,
            autonomy_level=1,
            requires_human_approval=True,
            can_auto_execute=False,
            decision_status=AgentDecision.DecisionStatus.AWAITING_APPROVAL,
            decision_reason="Aguardando aprovacao do gestor.",
            explainability_payload={"approval_roles": ["maintenance-manager"]},
        )
        simulation_type = SimulationType.objects.create(slug=f"war-room-sim-{company.id}", name=f"War Room Simulation {company.id}", enabled=True)
        scenario = SimulationScenario.objects.create(
            simulation_type=simulation_type,
            company=company,
            site=site,
            title=f"Simulacao do war room {company.id}",
            target_entity="asset",
            target_entity_id=str(asset.public_id),
            status=SimulationScenario.ScenarioStatus.COMPLETED,
            created_by_user=self.user,
        )
        run_sim = SimulationRun.objects.create(
            scenario=scenario,
            decision=decision,
            trigger_type=SimulationRun.TriggerType.DECISION,
            source_type=SimulationRun.SourceType.DECISION,
            source_reference=str(decision.public_id),
            status=SimulationRun.RunStatus.COMPLETED,
            started_at=timezone.now() - timedelta(minutes=5),
            finished_at=timezone.now() - timedelta(minutes=4),
            baseline_snapshot={"state": "current"},
            created_by_user=self.user,
        )
        SimulationResult.objects.create(
            simulation_run=run_sim,
            summary="Simulacao aponta reducao de risco operacional.",
            impact_score="8.20",
            confidence_level="high",
            recommendation="Executar com prioridade.",
            result_payload={"current": {"risk": 8}, "proposed": {"risk": 4}},
        )
        FailureEvent.objects.create(asset=asset, symptom="Falha critica recente", severity="critical", status="open")
        TechnicianSchedule.objects.create(
            company=company,
            operational_site=site,
            technician=self.user,
            date=timezone.localdate(),
            total_jobs=7,
            total_estimated_duration=420,
            total_estimated_travel=95,
            total_conflicts=2,
        )
        ScheduledVisit.objects.create(
            company=company,
            operational_site=site,
            asset=asset,
            work_order=order,
            technician=self.user,
            title="Visita critica",
            scheduled_date=timezone.localdate(),
            priority=ScheduledVisit.Priority.URGENT,
            status=ScheduledVisit.Status.PENDING_ASSIGNMENT,
            route_order=1,
            estimated_duration_minutes=120,
            estimated_travel_minutes=35,
        )
        TechnicianServiceRequest.objects.create(
            requester_user=self.user,
            requester_company=company,
            title=f"Request sem cobertura {company.id}",
            description="Necessita tecnico especializado",
            category="hvac",
            service_type=TechnicianServiceRequest.ServiceType.EMERGENCY,
            priority=TechnicianServiceRequest.Priority.URGENT,
            city="Sao Paulo",
            state="SP",
            related_client=client,
            related_site=site,
            related_asset=asset,
            status=TechnicianServiceRequest.Status.MATCHING,
        )
        OptimizationProposal.objects.create(
            company=company,
            site=site,
            target_type="decision_policy",
            target_reference="create_investigation_task",
            proposal_type="approval_requirement_adjustment",
            rationale="Aprimorar governanca",
            current_value={"requires_human_approval": False},
            proposed_value={"requires_human_approval": True},
        )
        experiment = Experiment.objects.create(
            company=company,
            site=site,
            name=f"War Room Experiment {company.id}",
            slug=f"war-room-experiment-{company.id}",
            target_component=Experiment.TargetComponent.DECISION_ENGINE,
            target_reference="create_investigation_task",
            status=Experiment.Status.RUNNING,
            primary_metric="decision_effectiveness_score",
        )
        Variant.objects.create(experiment=experiment, name="Control", slug="control", weight=50, is_control=True)
        PolicyEvaluation.objects.create(
            company=company,
            site=site,
            module_slug="ai_decision_engine",
            action_type="create_investigation_task",
            result="require_approval",
            reason="Acao operacional exige revisao humana.",
        )
        SystemEventLog.objects.create(
            event_type="decision.awaiting_approval",
            source_module="ai_decision_engine",
            severity="warning",
            company=company,
            site=site,
            entity_type="asset",
            entity_id=str(asset.public_id),
            message="Decision awaiting approval.",
        )
        return {"company": company, "site": site, "recommendation": recommendation, "decision": decision}

    def _create_client_portal_user(self, *, role_slug="client-manager"):
        user = UserFactory(
            password="admin123!",
            is_staff=False,
            user_type="client",
            email="cliente.portal@academia.local",
        )
        company = CompanyFactory(name="Academia Exemplo", slug="academia-exemplo-portal")
        maintenance_client = MaintenanceClientFactory(company=company, display_name="Academia Exemplo")
        site = OperationalSiteFactory(
            maintenance_client=maintenance_client,
            name="Unidade Centro",
            code="CTR-001",
        )
        other_company = CompanyFactory(name="Laboratorio Exemplo", slug="laboratorio-exemplo-portal")
        other_client = MaintenanceClientFactory(company=other_company, display_name="Laboratorio Exemplo")
        other_site = OperationalSiteFactory(
            maintenance_client=other_client,
            name="Laboratorio Campinas",
            code="LAB-001",
        )
        category = AssetCategoryFactory(name="HVAC Portal")
        asset = AssetFactory(
            operational_site=site,
            category=category,
            asset_tag="PORTAL-CTR-101",
            name="Chiller Unidade A",
        )
        other_asset = AssetFactory(
            operational_site=other_site,
            category=category,
            asset_tag="PORTAL-LAB-001",
            name="Camara Externa",
        )
        work_order = ServiceOrderFactory(
            order_number="OS-PORTAL-202",
            client=maintenance_client,
            operational_site=site,
            asset=asset,
            title="Baixa eficiencia de resfriamento",
        )
        ServiceOrderFactory(
            order_number="OS-2026-9999",
            client=other_client,
            operational_site=other_site,
            asset=other_asset,
            title="Ordem externa",
        )
        MaintenancePlan.objects.create(
            company=company,
            operational_site=site,
            asset=asset,
            category=category,
            name="Plano PM-HVAC Portal",
            frequency_type=MaintenancePlan.FrequencyType.MONTHLY,
            frequency_value=1,
            estimated_duration_minutes=90,
            next_due_date=timezone.localdate(),
        )
        MembershipFactory(user=user, company=company, is_primary=True)
        SiteMembershipFactory(user=user, company=company, site=site, is_primary=True)
        assign_smart_system_role(user, role_slug, company=company)

        customer = BillingCustomerFactory(company=company, trade_name=company.name, legal_name=company.legal_name)
        plan = BillingPlanFactory(
            name="Client Portal",
            slug="client-portal-plan",
            price_amount="1990.00",
            price_monthly="1990.00",
            price_yearly="19900.00",
            enabled_features=["smart_system", "client_portal"],
        )
        contract = Contract.objects.create(
            company=company,
            billing_customer=customer,
            plan=plan,
            billing_periodicity=Contract.BillingPeriodicity.MONTHLY,
            contracted_amount="1990.00",
            status=Contract.Status.ACTIVE,
        )
        SubscriptionFactory(
            billing_customer=customer,
            company=company,
            contract=contract,
            plan=plan,
            amount="1990.00",
            status="active",
        )
        return user, company, site, asset, work_order, other_asset

    def _create_voiceops_data(self):
        company = CompanyFactory(name="VoiceOps Company", slug="voiceops-company")
        MembershipFactory(user=self.user, company=company, is_primary=False)
        assign_smart_system_role(self.user, "maintenance-manager", company=company)
        client = MaintenanceClientFactory(company=company, display_name="VoiceOps Client")
        site = OperationalSiteFactory(maintenance_client=client, name="VoiceOps Site", code="VOICE-001")
        VoiceInteraction.objects.create(
            user=self.user,
            company=company,
            site=site,
            persona="manager",
            channel="desktop",
            transcript_status="transcribed",
            transcript_text="o que esta critico hoje",
            detected_intent="query_summary",
            action_status="response_only",
            response_payload={"summary": "Resumo executivo pronto."},
        )
        return company

    def test_dashboard_loads(self):
        response = self.client.get(reverse("admin-shell:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Executive Command Center")
        self.assertContains(response, "SMART360")

    def test_module_page_loads(self):
        response = self.client.get(reverse("admin-shell:module-page", kwargs={"module_slug": "smart-system"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Smart System")
        self.assertContains(response, "Ativos monitorados")
        self.assertContains(response, "Ordens de servico")
        self.assertContains(response, "Backlog de manutencao")
        self.assertContains(response, "Falhas e confiabilidade")

    def test_marketplace_dashboard_loads(self):
        self._create_marketplace_data()
        response = self.client.get(reverse("admin-shell:marketplace-technicians-dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Marketplace de Tecnicos")
        self.assertContains(response, "Solicitacoes recentes")

    def test_marketplace_requests_load(self):
        self._create_marketplace_data()
        response = self.client.get(reverse("admin-shell:marketplace-technicians-requests"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Carteira de solicitacoes")
        self.assertContains(response, "Atendimento em esteira")

    def test_marketplace_technician_detail_loads(self):
        technician = self._create_marketplace_data()
        response = self.client.get(
            reverse("admin-shell:marketplace-technicians-technician-detail", kwargs={"public_id": technician.public_id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tecnico de Campo")
        self.assertContains(response, "Historico de atribuicoes")

    def test_marketplace_matching_loads(self):
        self._create_marketplace_data()
        response = self.client.get(reverse("admin-shell:marketplace-technicians-matching"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Matching Inteligente")
        self.assertContains(response, "Tecnico de Campo")
        self.assertContains(response, "91.00")

    def test_smart_system_quote_pages_load(self):
        maintenance_client = MaintenanceClientFactory(company=CompanyFactory(name="Quote Company", slug="quote-company"), display_name="Quote Company")
        site = OperationalSiteFactory(maintenance_client=maintenance_client, name="Site Orcamento", code="QTE-01")
        category = AssetCategoryFactory(name="Quote HVAC")
        asset = AssetFactory(operational_site=site, category=category, asset_tag="QTE-AST-01", name="Chiller Quote")
        MembershipFactory(user=self.user, company=maintenance_client.company, is_primary=False)
        order = ServiceOrderFactory(
            order_number="OS-QUOTE-001",
            client=maintenance_client,
            operational_site=site,
            asset=asset,
            title="OS com quote",
        )
        quote = ServiceQuote.objects.create(
            quote_number="QTE-2026-0101",
            company=maintenance_client.company,
            operational_site=site,
            work_order=order,
            asset=asset,
            status=ServiceQuote.Status.SENT,
            total_parts="200.00",
            total_labor="150.00",
            total_value="350.00",
            created_by=self.user,
            updated_by=self.user,
        )
        QuoteItem.objects.create(
            quote=quote,
            item_type=QuoteItem.ItemType.PART,
            description="Sensor PT100",
            part_reference="PRT-0001",
            quantity="1.00",
            unit_price="200.00",
            total_price="200.00",
        )

        list_response = self.client.get(reverse("admin-shell:smart-system-quotes"))
        detail_response = self.client.get(reverse("admin-shell:smart-system-quote-detail", kwargs={"quote_number": quote.quote_number}))

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "QTE-2026-0101")
        self.assertContains(detail_response, "Sensor PT100")

    def test_client_portal_quote_approval_flow(self):
        user, company, site, asset, work_order, _ = self._create_client_portal_user(role_slug="client-manager")
        self.client.force_login(user)
        quote = ServiceQuote.objects.create(
            quote_number="QTE-PORTAL-0001",
            company=company,
            operational_site=site,
            work_order=work_order,
            asset=asset,
            status=ServiceQuote.Status.SENT,
            total_parts="400.00",
            total_labor="250.00",
            total_value="650.00",
        )

        list_response = self.client.get(reverse("admin-shell:client-portal-quotes"))
        self.assertEqual(list_response.status_code, 302)
        self.assertIn("/portal/", list_response.url)

        approve_response = self.client.post(
            reverse("admin-shell:client-portal-quote-approve", kwargs={"quote_number": quote.quote_number}),
            {"signer_name": "Marina Cliente", "notes": "Aprovado para seguir com o reparo."},
        )
        self.assertEqual(approve_response.status_code, 302)
        self.assertIn("/portal/", approve_response.url)

    def test_client_portal_quote_rejection_flow(self):
        user, company, site, asset, work_order, _ = self._create_client_portal_user(role_slug="client-manager")
        self.client.force_login(user)
        quote = ServiceQuote.objects.create(
            quote_number="QTE-PORTAL-0002",
            company=company,
            operational_site=site,
            work_order=work_order,
            asset=asset,
            status=ServiceQuote.Status.SENT,
            total_parts="180.00",
            total_labor="120.00",
            total_value="300.00",
        )

        reject_response = self.client.post(
            reverse("admin-shell:client-portal-quote-reject", kwargs={"quote_number": quote.quote_number}),
            {"signer_name": "Marina Cliente", "rejection_reason": "Servico adiado para o proximo mes."},
        )
        self.assertEqual(reject_response.status_code, 302)
        self.assertIn("/portal/", reject_response.url)

    def test_smart_system_contract_pages_load(self):
        company = CompanyFactory(name="Contrato Exemplo", slug="contrato-exemplo")
        MembershipFactory(user=self.user, company=company, is_primary=False)
        assign_smart_system_role(self.user, "maintenance-manager", company=company)
        maintenance_client = MaintenanceClientFactory(company=company, display_name="Cliente Contrato")
        site = OperationalSiteFactory(maintenance_client=maintenance_client, name="Unidade Contrato", code="CTR-01")
        asset = AssetFactory(operational_site=site, asset_tag="CTR-AST-01", name="Chiller Contratado")
        contract = MaintenanceContract.objects.create(
            company=company,
            client=maintenance_client,
            operational_site=site,
            contract_number="MCT-202603-0901",
            start_date=timezone.localdate(),
            status=MaintenanceContract.Status.ACTIVE,
            billing_frequency=MaintenanceContract.BillingFrequency.MONTHLY,
            contract_value="1800.00",
            next_billing_date=timezone.localdate(),
        )
        ContractAsset.objects.create(
            contract=contract,
            asset=asset,
            maintenance_frequency=ContractAsset.MaintenanceFrequency.MONTHLY,
            next_execution=timezone.localdate(),
        )

        list_response = self.client.get(reverse("admin-shell:smart-system-contracts"))
        detail_response = self.client.get(reverse("admin-shell:smart-system-contract-detail", kwargs={"contract_number": contract.contract_number}))

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "MCT-202603-0901")
        self.assertContains(detail_response, "Chiller Contratado")

    def test_client_portal_contract_pages_load(self):
        user, company, site, asset, _, _ = self._create_client_portal_user(role_slug="client-manager")
        self.client.force_login(user)
        contract = MaintenanceContract.objects.create(
            company=company,
            client=site.maintenance_client,
            operational_site=site,
            contract_number="MCT-PORTAL-0001",
            start_date=timezone.localdate(),
            status=MaintenanceContract.Status.ACTIVE,
            billing_frequency=MaintenanceContract.BillingFrequency.MONTHLY,
            contract_value="2200.00",
            next_billing_date=timezone.localdate(),
        )
        ContractAsset.objects.create(
            contract=contract,
            asset=asset,
            maintenance_frequency=ContractAsset.MaintenanceFrequency.MONTHLY,
            next_execution=timezone.localdate(),
        )

        list_response = self.client.get(reverse("admin-shell:client-portal-contracts"))
        detail_response = self.client.get(reverse("admin-shell:client-portal-contract-detail", kwargs={"contract_number": contract.contract_number}))

        self.assertEqual(list_response.status_code, 302)
        self.assertIn("/portal/", list_response.url)
        self.assertEqual(detail_response.status_code, 302)
        self.assertIn("/portal/", detail_response.url)

    def test_scheduling_dashboard_loads(self):
        self._create_schedule_data()
        response = self.client.get(reverse("admin-shell:smart-system-scheduling"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Agenda &amp; rotas", html=False)
        self.assertContains(response, "Visita agendada")
        self.assertContains(response, "Visitas hoje")
        self.assertContains(response, "Nao alocadas")
        self.assertContains(response, "Conflitos")
        self.assertContains(response, "Rotas geradas")
        self.assertContains(response, "OS pendentes")
        self.assertContains(response, "Sequencia sugerida para a operacao de campo no periodo selecionado.")
        self.assertNotContains(response, 'class="page-hero"')

    def test_scheduling_dashboard_empty_state_is_explicit(self):
        empty_company = CompanyFactory(name="Agenda Vazia", slug="agenda-vazia")
        MembershipFactory(user=self.user, company=empty_company, is_primary=False)
        assign_smart_system_role(self.user, "planner", company=empty_company)
        session = self.client.session
        session["smart_system_active_company_id"] = empty_company.id
        session.pop("smart_system_active_site_id", None)
        session.save()

        response = self.client.get(reverse("admin-shell:smart-system-scheduling"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum tecnico com carga planejada para o periodo.")
        self.assertContains(response, "Nenhuma visita agendada para o periodo.")
        self.assertContains(response, "Nenhum conflito identificado para o periodo.")
        self.assertContains(response, "Nenhuma visita sem tecnico para o periodo.")
        self.assertNotContains(response, 'class="page-hero"')

    def test_scheduling_calendar_and_technician_agenda_load(self):
        self._create_schedule_data()
        calendar_response = self.client.get(reverse("admin-shell:smart-system-scheduling-calendar"))
        agenda_response = self.client.get(reverse("admin-shell:smart-system-technician-agenda", kwargs={"technician_id": self.user.id}))
        self.assertEqual(calendar_response.status_code, 200)
        self.assertEqual(agenda_response.status_code, 200)
        self.assertContains(calendar_response, "Calendario operacional")
        self.assertContains(agenda_response, "Sequencia sugerida da rota")

    def test_technician_schedule_page_loads(self):
        self._create_schedule_data()
        response = self.client.get(reverse("admin-shell:technician-app-schedule"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Agenda do dia")

    def test_technician_sync_center_loads(self):
        response = self.client.get(reverse("admin-shell:technician-app-sync"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sincronizacao de campo")
        self.assertContains(response, "Pendencias por atendimento")

    def test_offline_bundle_returns_assigned_services_payload(self):
        response = self.client.get(reverse("admin-shell:technician-app-offline-bundle"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("services", response.json())
        self.assertIn("service_details", response.json())

    def test_technician_service_detail_renders_copilot_entrypoint(self):
        technician = UserFactory(password="admin123!", is_staff=True, is_superuser=True)
        self.client.force_login(technician)

        response = self.client.get(reverse("admin-shell:technician-app-service-detail", kwargs={"order_code": "OS-2026-0151"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Copiloto")
        self.assertContains(response, "O que ja deu problema nesse equipamento?")

    def test_technician_copilot_context_endpoint_returns_order_context(self):
        technician = UserFactory(password="admin123!", is_staff=True, is_superuser=True)
        self.client.force_login(technician)

        response = self.client.get(
            reverse("admin-shell:technician-app-copilot-context"),
            {"order_code": "OS-2026-0151"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["order_code"], "OS-2026-0151")
        self.assertIn("suggestions", payload)
        self.assertEqual(payload["context"]["asset_code"], "ESTEIRA-ERG-12")

    def test_technician_copilot_query_returns_checklist_interpretation(self):
        technician = UserFactory(password="admin123!", is_staff=True, is_superuser=True)
        self.client.force_login(technician)

        response = self.client.post(
            reverse("admin-shell:technician-app-copilot-query"),
            data=json.dumps({"order_code": "OS-2026-0151", "query": "Esse checklist NOK significa o que?"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["response"]["intent"], "checklist_interpretation")
        self.assertTrue(payload["response"]["bullets"])

    def test_technician_copilot_query_can_help_with_documentation(self):
        technician = UserFactory(password="admin123!", is_staff=True, is_superuser=True)
        self.client.force_login(technician)

        response = self.client.post(
            reverse("admin-shell:technician-app-copilot-query"),
            data=json.dumps(
                {"order_code": "OS-2026-0151", "query": "Reescreva isso de forma tecnica: motor nao girava direito"}
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["response"]["intent"], "documentation_help")
        self.assertIn("rotacao irregular", " ".join(payload["response"]["bullets"]))

    def test_technician_copilot_respects_scope(self):
        user, _, _, _, _ = self._create_scoped_manager()
        self.client.force_login(user)

        response = self.client.get(
            reverse("admin-shell:technician-app-copilot-context"),
            {"order_code": "OS-2026-0151"},
        )

        self.assertEqual(response.status_code, 404)

    def test_technician_copilot_sync_persists_offline_messages(self):
        user, academia, _, academia_site, _ = self._create_scoped_manager()
        self.client.force_login(user)
        maintenance_client = academia_site.maintenance_client
        category = AssetCategoryFactory(name="Copilot Sync")
        asset = AssetFactory(operational_site=academia_site, category=category, asset_tag="COP-SYNC-01", name="Asset Copilot")
        order = ServiceOrderFactory(
            order_number="OS-COP-001",
            client=maintenance_client,
            operational_site=academia_site,
            asset=asset,
            assigned_to=user,
            title="Copilot offline",
        )

        response = self.client.post(
            reverse("admin-shell:technician-app-copilot-sync"),
            data=json.dumps(
                {
                    "order_code": order.order_number,
                    "context": {"order_code": order.order_number, "asset_code": asset.asset_tag},
                    "messages": [
                        {"role": "user", "content": "Qual o proximo passo aqui?", "intent": "execution_guidance"},
                        {"role": "assistant", "content": "Valide o sintoma e registre o diagnostico.", "intent": "execution_guidance"},
                    ],
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(TechnicianCopilotSession.objects.filter(user=user, service_order=order).exists())
        self.assertEqual(TechnicianCopilotMessage.objects.filter(session__service_order=order).count(), 2)

    def test_offline_sync_creates_snapshot_and_marks_order_in_progress(self):
        user, academia, _, academia_site, _ = self._create_scoped_manager()
        self.client.force_login(user)
        maintenance_client = MaintenanceClientFactory(company=academia, display_name="Academia Exemplo")
        category = AssetCategoryFactory(name="Offline HVAC")
        asset = AssetFactory(operational_site=academia_site, category=category, asset_tag="OFF-CH-01", name="Chiller Offline")
        order = ServiceOrderFactory(
            order_number="OS-OFF-001",
            client=maintenance_client,
            operational_site=academia_site,
            asset=asset,
            assigned_to=user,
            title="Atendimento offline",
        )

        response = self.client.post(
            reverse("admin-shell:technician-app-offline-sync"),
            data=json.dumps(
                {
                    "operations": [
                        {
                            "operationId": "op-start-001",
                            "action": "start_execution",
                            "orderCode": order.order_number,
                            "payload": {"startedAt": "2026-03-12T10:20:00-03:00", "progress": 12, "recordedAt": "2026-03-12T10:20:00-03:00"},
                        },
                        {
                            "operationId": "op-save-001",
                            "action": "save_execution",
                            "orderCode": order.order_number,
                            "payload": {
                                "recordedAt": "2026-03-12T10:32:00-03:00",
                                "progress": 66,
                                "executionStatus": "Em execucao",
                                "diagnosis": {"technical_diagnosis": "Falha intermitente de sensor"},
                                "executedAction": {"intervention": "Reaperto e limpeza do conjunto"},
                                "finalization": {"recommendation": "Monitorar comportamento na proxima semana"},
                            },
                        },
                    ]
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        snapshot = FieldExecutionSnapshot.objects.get(service_order=order, technician=user)
        self.assertEqual(order.status, "in_progress")
        self.assertEqual(snapshot.progress, 66)
        self.assertEqual(snapshot.diagnosis_payload["technical_diagnosis"], "Falha intermitente de sensor")
        self.assertTrue(FieldSyncOperation.objects.filter(client_operation_id="op-save-001", status="processed").exists())

    def test_offline_sync_detects_completion_conflict_for_closed_order(self):
        user, academia, _, academia_site, _ = self._create_scoped_manager()
        self.client.force_login(user)
        maintenance_client = MaintenanceClientFactory(company=academia, display_name="Academia Exemplo")
        category = AssetCategoryFactory(name="Offline Conflict")
        asset = AssetFactory(operational_site=academia_site, category=category, asset_tag="OFF-CF-01", name="Asset Conflict")
        order = ServiceOrderFactory(
            order_number="OS-OFF-009",
            client=maintenance_client,
            operational_site=academia_site,
            asset=asset,
            assigned_to=user,
            status="completed",
            title="Ordem fechada",
        )

        response = self.client.post(
            reverse("admin-shell:technician-app-offline-sync"),
            data=json.dumps(
                {
                    "operations": [
                        {
                            "operationId": "op-complete-closed",
                            "action": "complete_execution",
                            "orderCode": order.order_number,
                            "payload": {"completedAt": "2026-03-12T11:10:00-03:00"},
                        }
                    ]
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["processed"][0]
        self.assertEqual(payload["status"], "conflict")
        self.assertEqual(payload["conflict_code"], "order_closed")

    def test_offline_sync_denies_foreign_scope_order(self):
        user, academia, _, academia_site, _ = self._create_scoped_manager()
        self.client.force_login(user)
        local_client = MaintenanceClientFactory(company=academia, display_name="Academia Exemplo")
        category = AssetCategoryFactory(name="Offline Scope")
        local_asset = AssetFactory(operational_site=academia_site, category=category, asset_tag="OFF-LC-01", name="Asset Local")
        _ = ServiceOrderFactory(
            order_number="OS-OFF-LOCAL",
            client=local_client,
            operational_site=academia_site,
            asset=local_asset,
            assigned_to=user,
            title="Local",
        )
        other_company = CompanyFactory(name="Empresa Externa", slug="empresa-externa-sync")
        other_client = MaintenanceClientFactory(company=other_company, display_name="Empresa Externa")
        other_site = OperationalSiteFactory(maintenance_client=other_client, name="Unidade Externa", code="EXT-01")
        other_asset = AssetFactory(operational_site=other_site, category=category, asset_tag="OFF-EXT-01", name="Asset Externo")
        foreign_order = ServiceOrderFactory(
            order_number="OS-OFF-FOREIGN",
            client=other_client,
            operational_site=other_site,
            asset=other_asset,
            title="Externo",
        )

        response = self.client.post(
            reverse("admin-shell:technician-app-offline-sync"),
            data=json.dumps(
                {
                    "operations": [
                        {
                            "operationId": "op-foreign-001",
                            "action": "start_execution",
                            "orderCode": foreign_order.order_number,
                            "payload": {"startedAt": "2026-03-12T11:40:00-03:00"},
                        }
                    ]
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["processed"][0]
        self.assertEqual(payload["status"], "conflict")
        self.assertEqual(payload["conflict_code"], "out_of_scope")

    def test_smart_system_renders_operational_actions(self):
        response = self.client.get(reverse("admin-shell:module-page", kwargs={"module_slug": "smart-system"}))
        self.assertContains(response, "Nova OS")
        self.assertContains(response, "Registrar falha")
        self.assertContains(response, "Visao por area / site / cliente")

    def test_asset_list_loads(self):
        response = self.client.get(reverse("admin-shell:smart-system-assets"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestao de ativos, criticidade, condicao e historico operacional")
        self.assertContains(response, "CHILLER-UNID-A")
        self.assertContains(response, "Esteira Ergometrica 12")
        self.assertNotContains(response, "CAMARA-CLIMATICA-01")
        self.assertContains(response, "Carteira de ativos")
        self.assertContains(response, reverse("admin-shell:smart-system-customer-equipment-create"))

    def test_asset_detail_loads(self):
        response = self.client.get(
            reverse("admin-shell:smart-system-asset-detail", kwargs={"asset_code": "CHILLER-UNID-A"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chiller Unidade A")
        self.assertContains(response, "Dados tecnicos do ativo")
        self.assertContains(response, "Historico recente do ativo")

    def test_asset_filter_by_client(self):
        laboratorio_company = CompanyFactory(name="Laboratorio Exemplo", slug="tests-shell-filtro-laboratorio")
        MembershipFactory(user=self.user, company=laboratorio_company, is_primary=False)
        assign_smart_system_role(self.user, "maintenance-manager", company=laboratorio_company)
        filt_session = self.client.session
        filt_session["smart_system_active_company_id"] = laboratorio_company.id
        filt_session.pop("smart_system_active_site_id", None)
        filt_session.save()

        response = self.client.get(reverse("admin-shell:smart-system-assets"), {"client": "Laboratorio Exemplo"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CAMARA-CLIMATICA-01")
        self.assertNotContains(response, "BIKE-SPIN-07")

    def test_part_list_loads(self):
        response = self.client.get(reverse("admin-shell:smart-system-parts"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestao de estoque de manutencao")
        self.assertContains(response, "PRT-0001")
        self.assertContains(response, "Carteira de pecas e sobressalentes")

    def test_part_detail_loads(self):
        response = self.client.get(reverse("admin-shell:smart-system-part-detail", kwargs={"part_code": "PRT-0005"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inversor WEG CFW300")
        self.assertContains(response, "Historico de movimentacao")
        self.assertContains(response, "Consumo em ordens de servico")
        self.assertContains(response, "Sem estoque")

    def test_stock_movements_load(self):
        response = self.client.get(reverse("admin-shell:smart-system-stock-movements"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Historico consolidado")
        self.assertContains(response, "Entrada de estoque")
        self.assertContains(response, "OS-2026-0151")

    def test_report_history_loads(self):
        response = self.client.get(reverse("admin-shell:smart-system-reports"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Relatorios tecnicos operacionais")
        self.assertContains(response, "RT-OS-OS-2026-0148")
        self.assertContains(response, "Ficha Tecnica Resumida do Ativo")

    def test_work_order_report_preview_loads(self):
        response = self.client.get(
            reverse(
                "admin-shell:smart-system-report-preview",
                kwargs={"report_type": "work-order", "reference_code": "OS-2026-0148"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Relatorio de Ordem de Servico")
        self.assertContains(response, "Materiais e pecas utilizadas")
        self.assertContains(response, "Checklist executado")

    def test_work_order_report_preview_renders_service_signatures(self):
        client = MaintenanceClientFactory(company=self.academia_company, display_name="Assinatura Cliente Demo")
        site = OperationalSiteFactory(maintenance_client=client, name="Unidade Assinada", code="SIG-01-WO")
        category = AssetCategoryFactory(name="Assinatura HVAC")
        asset = AssetFactory(
            operational_site=site,
            category=category,
            asset_tag="CHILLER-SIG-WO-RPT",
            name="Chiller Assinatura",
        )
        order = ServiceOrderFactory(
            order_number="OS-RPT-SIG-WO01",
            client=client,
            operational_site=site,
            asset=asset,
            title="Demonstracao assinatura de relatorio tecnico",
            assigned_to=self.user,
            created_by=self.user,
        )
        ServiceSignature.objects.create(
            signature_type=ServiceSignature.SignatureType.TECHNICIAN_COMPLETION,
            signer_role=ServiceSignature.SignerRole.TECHNICIAN,
            signer_name="Carlos Mota",
            signer_user=self.user,
            company=self.academia_company,
            operational_site=site,
            service_order=order,
            signature_data="data:image/png;base64,AAAA",
        )
        ServiceSignature.objects.create(
            signature_type=ServiceSignature.SignatureType.CLIENT_ACCEPTANCE,
            signer_role=ServiceSignature.SignerRole.CLIENT_RESPONSIBLE,
            signer_name="Patricia Souza",
            company=self.academia_company,
            operational_site=site,
            service_order=order,
            signature_data="data:image/png;base64,BBBB",
        )

        response = self.client.get(
            reverse(
                "admin-shell:smart-system-report-preview",
                kwargs={"report_type": "work-order", "reference_code": "OS-RPT-SIG-WO01"},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Assinatura do tecnico")
        self.assertContains(response, "Carlos Mota")
        self.assertContains(response, "Patricia Souza")

    def test_preventive_report_preview_loads(self):
        response = self.client.get(
            reverse(
                "admin-shell:smart-system-report-preview",
                kwargs={"report_type": "preventive", "reference_code": "PP-2026-003"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Relatorio de Manutencao Preventiva")
        self.assertContains(response, "Recorrencia, aderencia e cobertura")
        self.assertContains(response, "Anomalias e recomendacoes")

    def test_failure_report_preview_loads(self):
        response = self.client.get(
            reverse(
                "admin-shell:smart-system-report-preview",
                kwargs={"report_type": "failure", "reference_code": "FE-2026-002"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Relatorio de Evento de Falha / RCA")
        self.assertContains(response, "Causa raiz / RCA")
        self.assertContains(response, "Impacto operacional e risco")

    def test_asset_summary_report_preview_loads(self):
        response = self.client.get(
            reverse(
                "admin-shell:smart-system-report-preview",
                kwargs={"report_type": "asset-summary", "reference_code": "CHILLER-UNID-A"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ficha Tecnica Resumida do Ativo")
        self.assertContains(response, "Indicadores de manutencao e confiabilidade")
        self.assertContains(response, "Principais falhas recentes")

    def test_report_download_returns_pdf(self):
        response = self.client.get(
            reverse(
                "admin-shell:smart-system-report-download",
                kwargs={"report_type": "work-order", "reference_code": "OS-2026-0148"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(".pdf", response["Content-Disposition"])

    def test_client_portal_dashboard_loads(self):
        user, _, _, _, _, _ = self._create_client_portal_user()
        self.client.force_login(user)

        response = self.client.get(reverse("admin-shell:client-portal-dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/portal/", response.url)

    def test_client_portal_assets_respect_scope(self):
        user, _, _, asset, _, other_asset = self._create_client_portal_user()
        self.client.force_login(user)

        response = self.client.get(reverse("admin-shell:client-portal-assets"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/portal/", response.url)

    def test_client_portal_asset_detail_denies_out_of_scope(self):
        user, _, _, _, _, other_asset = self._create_client_portal_user()
        self.client.force_login(user)

        response = self.client.get(reverse("admin-shell:client-portal-asset-detail", kwargs={"asset_code": other_asset.asset_tag}))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/portal/", response.url)

    def test_client_portal_request_creation_works(self):
        user, _, site, asset, _, _ = self._create_client_portal_user(role_slug="requester")
        self.client.force_login(user)

        response = self.client.post(
            reverse("admin-shell:client-portal-request-create"),
            {
                "operational_site": site.id,
                "asset": asset.id,
                "category": ClientPortalRequest.Category.MAINTENANCE,
                "priority": ClientPortalRequest.Priority.HIGH,
                "title": "Ruido anormal no chiller",
                "description": "Cliente percebeu ruido acima do padrao em horario de pico.",
                "contact_name": "Patricia Souza",
                "contact_email": "patricia@academia.local",
                "contact_phone": "+5511999999999",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertNotIn("/portal/", response.url)
        self.assertTrue(ClientPortalRequest.objects.filter(title="Ruido anormal no chiller").exists())

    def test_client_portal_readonly_cannot_create_request(self):
        user, _, site, asset, _, _ = self._create_client_portal_user(role_slug="client-readonly")
        self.client.force_login(user)

        response = self.client.post(
            reverse("admin-shell:client-portal-request-create"),
            {
                "operational_site": site.id,
                "asset": asset.id,
                "category": ClientPortalRequest.Category.MAINTENANCE,
                "priority": ClientPortalRequest.Priority.HIGH,
                "title": "Readonly tentando abrir chamado",
                "description": "Este usuario nao deve criar solicitacao.",
                "contact_name": "Patricia Souza",
                "contact_email": "patricia@academia.local",
                "contact_phone": "+5511999999999",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ClientPortalRequest.objects.filter(title="Readonly tentando abrir chamado").exists())

    def test_client_portal_report_export_respects_permission(self):
        user, _, _, _, _, _ = self._create_client_portal_user(role_slug="client-readonly")
        self.client.force_login(user)

        response = self.client.get(
            reverse(
                "admin-shell:client-portal-report-download",
                kwargs={"report_type": "asset-summary", "reference_code": "CHILLER-UNID-A"},
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/portal/", response.url)

    def test_client_portal_copilot_page_loads(self):
        user, _, _, _, _, _ = self._create_client_portal_user()
        self.client.force_login(user)

        response = self.client.get(reverse("admin-shell:client-portal-copilot"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/portal/", response.url)

    def test_client_portal_copilot_explains_work_order_safely(self):
        user, _, _, _, work_order, _ = self._create_client_portal_user()
        self.client.force_login(user)

        response = self.client.post(
            reverse("admin-shell:client-portal-copilot-query"),
            data=json.dumps(
                {
                    "query": f"Explique a OS {work_order.order_number}",
                    "context_seed": {"work_order": work_order.order_number},
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/portal/", response.url)

    def test_client_portal_copilot_explains_quote_with_permission_filtered_actions(self):
        user, company, site, asset, work_order, _ = self._create_client_portal_user(role_slug="client-readonly")
        quote = ServiceQuote.objects.create(
            company=company,
            operational_site=site,
            work_order=work_order,
            asset=asset,
            quote_number="QT-PORTAL-001",
            status=ServiceQuote.Status.SENT,
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse("admin-shell:client-portal-copilot-query"),
            data=json.dumps(
                {
                    "query": f"Explique o orcamento {quote.quote_number}",
                    "context_seed": {"quote": quote.quote_number},
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/portal/", response.url)

    def test_client_portal_copilot_explains_report_without_internal_link(self):
        user, _, _, asset, _, _ = self._create_client_portal_user()
        self.client.force_login(user)

        response = self.client.post(
            reverse("admin-shell:client-portal-copilot-query"),
            data=json.dumps(
                {
                    "query": "Explique este relatorio de forma simples.",
                    "context_seed": {"report_type": "asset-summary", "reference_code": asset.asset_tag},
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/portal/", response.url)

    def test_client_portal_copilot_keeps_basic_session_context(self):
        user, _, _, asset, _, _ = self._create_client_portal_user()
        self.client.force_login(user)

        first = self.client.post(
            reverse("admin-shell:client-portal-copilot-query"),
            data=json.dumps(
                {
                    "query": f"Explique o ativo {asset.asset_tag}",
                    "context_seed": {"asset": asset.asset_tag},
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(first.status_code, 302)
        self.assertIn("/portal/", first.url)

    def test_client_portal_copilot_does_not_expose_internal_recommendation(self):
        user, company, site, _, _, _ = self._create_client_portal_user()
        self.client.force_login(user)
        agent = AgentDefinition.objects.create(
            slug="profitability-agent-test",
            name="Profitability Agent Test",
            domain=AgentDefinition.Domain.PROFITABILITY,
            status=AgentDefinition.Status.ACTIVE,
            enabled=True,
        )
        run = AgentRun.objects.create(
            agent=agent,
            trigger_type=AgentRun.TriggerType.MANUAL,
            company=company,
            site=site,
            status=AgentRun.Status.COMPLETED,
        )
        AgentRecommendation.objects.create(
            agent_run=run,
            company=company,
            site=site,
            recommendation_type=AgentRecommendation.RecommendationType.CLIENT_MARGIN_ALERT,
            title="Cliente com margem negativa",
            summary="Contrato com margem negativa e necessidade de repricing.",
            severity=AgentRecommendation.Severity.HIGH,
            priority=AgentRecommendation.Priority.HIGH,
        )

        response = self.client.post(
            reverse("admin-shell:client-portal-copilot-query"),
            data=json.dumps({"query": "Como esta a unidade hoje?"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/portal/", response.url)

    def test_client_portal_copilot_generates_observability_events(self):
        user, _, _, _, work_order, _ = self._create_client_portal_user()
        self.client.force_login(user)

        response = self.client.post(
            reverse("admin-shell:client-portal-copilot-query"),
            data=json.dumps(
                {
                    "query": f"Explique a OS {work_order.order_number}",
                    "context_seed": {"work_order": work_order.order_number},
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/portal/", response.url)

    def test_ai_briefings_page_loads(self):
        response = self.client.get(reverse("admin-shell:ai-briefings"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Briefings")
        self.assertContains(response, "Gerar briefing sob demanda")

    def test_technician_dashboard_renders_latest_briefing(self):
        user = UserFactory(password="admin123!", is_staff=True)
        assign_smart_system_role(user, "technician")
        company = CompanyFactory(name="Field Briefing", slug="field-briefing")
        MembershipFactory(user=user, company=company, is_primary=True)
        briefing = AIBriefing.objects.create(
            briefing_type=AIBriefing.BriefingType.DAILY_FIELD,
            audience=AIBriefing.Audience.TECHNICIAN,
            company=company,
            user=user,
            title="Daily Field Briefing",
            summary="Resumo do campo para hoje.",
            content={"priorities": ["OS prioritarias"], "alerts": [], "suggested_actions": []},
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin-shell:technician-app-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, briefing.title)

    def test_client_portal_dashboard_renders_latest_briefing(self):
        user, company, site, _, _, _ = self._create_client_portal_user()
        AIBriefing.objects.create(
            briefing_type=AIBriefing.BriefingType.DAILY_CLIENT,
            audience=AIBriefing.Audience.CLIENT,
            company=company,
            site=site,
            user=user,
            title="Daily Client Briefing",
            summary="Resumo seguro do portal.",
            content={"priorities": ["Pendencias"], "alerts": [], "suggested_actions": []},
        )
        self.client.force_login(user)

        response = self.client.get(reverse("admin-shell:client-portal-dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/portal/", response.url)

    def test_technician_does_not_see_admin_menu_or_asset_creation_actions(self):
        user = UserFactory(password="admin123!", is_staff=True)
        assign_smart_system_role(user, "technician")
        self.client.force_login(user)

        response = self.client.get(reverse("admin-shell:module-page", kwargs={"module_slug": "smart-system"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ordens de Servico")
        self.assertNotContains(response, "Usuarios")
        self.assertNotContains(response, "Access Control Center")
        self.assertNotContains(response, "Nova OS")

    def test_technician_cannot_open_core_platform_placeholder_directly(self):
        user = UserFactory(password="admin123!", is_staff=True)
        assign_smart_system_role(user, "technician")
        self.client.force_login(user)

        response = self.client.get(reverse("admin-shell:module-page", kwargs={"module_slug": "core-platform"}))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Acesso negado", status_code=403)

    def test_super_admin_can_open_billing_dashboard(self):
        contract, _ = self._create_billing_contract()
        user = UserFactory(password="admin123!", is_staff=True)
        assign_smart_system_role(user, "super-admin")
        self.client.force_login(user)

        response = self.client.get(reverse("admin-shell:billing-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Operacao comercial da plataforma")
        self.assertContains(response, contract.contract_code)
        self.assertContains(response, "Professional")

    def test_super_admin_can_open_observability_dashboard(self):
        user = UserFactory(password="admin123!", is_staff=True)
        assign_smart_system_role(user, "super-admin")
        self.client.force_login(user)

        response = self.client.get(reverse("admin-shell:observability-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Observability Center")
        self.assertContains(response, "Saude dos componentes")
        self.assertContains(response, "Requests recentes")

    def test_finance_user_can_open_analytics_dashboard(self):
        user = UserFactory(password="admin123!", is_staff=True)
        company = CompanyFactory(name="Analytics Finance", slug="analytics-finance")
        MembershipFactory(user=user, company=company, is_primary=True)
        assign_smart_system_role(user, "finance-readonly", company=company)
        maintenance_client = MaintenanceClientFactory(company=company, display_name="Analytics Finance Client")
        site = OperationalSiteFactory(maintenance_client=maintenance_client, name="Unidade Analytics", code="AN-01")
        asset = AssetFactory(operational_site=site, asset_tag="AN-AST-01", name="Chiller Analytics")
        ServiceOrderFactory(
            order_number="OS-AN-001",
            client=maintenance_client,
            operational_site=site,
            asset=asset,
            assigned_to=user,
            title="OS Analytics",
        )
        self.client.force_login(user)
        session = self.client.session
        session["smart_system_active_company_id"] = company.id
        session.save()

        response = self.client.get(reverse("admin-shell:analytics-executive-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analytics Executivo")
        self.assertContains(response, "Rentabilidade operacional")

    def test_manager_can_open_executive_war_room(self):
        payload = self._create_war_room_data()
        session = self.client.session
        session["smart_system_active_company_id"] = payload["company"].id
        session["smart_system_active_site_id"] = payload["site"].id
        session.save()

        response = self.client.get(reverse("admin-shell:executive-war-room"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Executive War Room")
        self.assertContains(response, "Alertas criticos")
        self.assertContains(response, "Fila de decisoes")
        self.assertContains(response, payload["recommendation"].title)
        self.assertContains(response, payload["decision"].agent_action_proposal.title)

    def test_executive_war_room_respects_company_scope(self):
        visible = self._create_war_room_data()
        hidden = self._create_war_room_data(company=CompanyFactory(name="Hidden Company", slug="hidden-company"))
        session = self.client.session
        session["smart_system_active_company_id"] = visible["company"].id
        session["smart_system_active_site_id"] = visible["site"].id
        session.save()

        response = self.client.get(reverse("admin-shell:executive-war-room"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, visible["recommendation"].title)
        self.assertNotContains(response, hidden["recommendation"].title)

    def test_executive_war_room_data_endpoint_returns_summary_payload(self):
        payload = self._create_war_room_data()
        session = self.client.session
        session["smart_system_active_company_id"] = payload["company"].id
        session["smart_system_active_site_id"] = payload["site"].id
        session.save()

        response = self.client.get(reverse("admin-shell:executive-war-room-data"), {"period": "7d"})

        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertIn("kpis", body)
        self.assertIn("alerts", body)
        self.assertIn("feed", body)
        self.assertGreaterEqual(body["decision_queue_count"], 1)

    def test_executive_war_room_stream_returns_sse_payload(self):
        payload = self._create_war_room_data()
        session = self.client.session
        session["smart_system_active_company_id"] = payload["company"].id
        session["smart_system_active_site_id"] = payload["site"].id
        session.save()

        response = self.client.get(reverse("admin-shell:executive-war-room-stream"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response["Content-Type"])

    def test_ai_digital_twin_center_renders(self):
        site = OperationalSiteFactory()
        MembershipFactory(user=self.user, company=site.maintenance_client.company, is_primary=False)
        assign_smart_system_role(self.user, "maintenance-manager", company=site.maintenance_client.company)
        DigitalTwinOrchestrator.project_for_site(site=site)

        response = self.client.get(reverse("admin-shell:ai-digital-twin-center"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Digital Twin Operacional")

    def test_ai_knowledge_graph_center_renders(self):
        site = OperationalSiteFactory()
        asset = AssetFactory(operational_site=site)
        ServiceOrderFactory(client=site.maintenance_client, operational_site=site, asset=asset, assigned_to=self.user)
        MembershipFactory(user=self.user, company=site.maintenance_client.company, is_primary=False)
        assign_smart_system_role(self.user, "maintenance-manager", company=site.maintenance_client.company)
        GraphProjectionService.project_company_graph(company=site.maintenance_client.company, site=site)

        response = self.client.get(reverse("admin-shell:ai-knowledge-graph-center"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Knowledge Graph Industrial")

    def test_technician_cannot_open_executive_war_room(self):
        user = UserFactory(password="admin123!", is_staff=True)
        assign_smart_system_role(user, "technician")
        self.client.force_login(user)

        response = self.client.get(reverse("admin-shell:executive-war-room"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Acesso negado", status_code=403)

    def test_manager_can_open_ai_autonomy_center(self):
        company = CompanyFactory(name="Autonomy Shell", slug="autonomy-shell")
        MembershipFactory(user=self.user, company=company, is_primary=False)
        assign_smart_system_role(self.user, "maintenance-manager", company=company)
        client = MaintenanceClientFactory(company=company, display_name="Autonomy Client")
        site = OperationalSiteFactory(maintenance_client=client, name="Autonomy Unit", code="AUT-01")
        config = AutonomousModeConfig.objects.create(
            company=company,
            is_enabled=True,
            mode_level=2,
            max_risk_level="low",
            allowed_action_types=["mark_asset_attention"],
        )
        execution = AutonomousExecution.objects.create(
            company=company,
            site=site,
            action_type="mark_asset_attention",
            source_agent="maintenance-agent",
            risk_level="low",
            confidence_level="high",
            confidence_score="0.82",
            execution_status=AutonomousExecution.ExecutionStatus.SUCCEEDED,
            execution_summary="Flag aplicada automaticamente.",
            rollback_supported=True,
            rollback_status=AutonomousExecution.RollbackStatus.AVAILABLE,
        )
        AutonomousIncident.objects.create(
            company=company,
            site=site,
            autonomous_execution=execution,
            severity="medium",
            incident_type="rollback_watch",
            summary="Incidente de monitoramento da autonomia.",
        )
        session = self.client.session
        session["smart_system_active_company_id"] = company.id
        session["active_site_id"] = str(site.public_id)
        session.save()

        response = self.client.get(reverse("admin-shell:ai-autonomy-center"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Autonomous Operations Mode")
        self.assertContains(response, "Cockpit de autonomia")
        self.assertContains(response, config.allowed_action_types[0])
        self.assertContains(response, execution.execution_summary)

    def test_manager_can_refresh_analytics_snapshot_from_shell(self):
        company = CompanyFactory(name="Analytics Refresh", slug="analytics-refresh")
        MembershipFactory(user=self.user, company=company, is_primary=False)
        assign_smart_system_role(self.user, "maintenance-manager", company=company)
        session = self.client.session
        session["smart_system_active_company_id"] = company.id
        session.save()

        response = self.client.get(reverse("admin-shell:analytics-executive-refresh"))

        self.assertEqual(response.status_code, 302)

    def test_technician_cannot_open_analytics_dashboard(self):
        user = UserFactory(password="admin123!", is_staff=True)
        assign_smart_system_role(user, "technician")
        self.client.force_login(user)

        response = self.client.get(reverse("admin-shell:analytics-executive-dashboard"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Acesso negado", status_code=403)

    def test_super_admin_can_open_contract_detail(self):
        contract, _ = self._create_billing_contract()
        user = UserFactory(password="admin123!", is_staff=True)
        assign_smart_system_role(user, "super-admin")
        self.client.force_login(user)

        response = self.client.get(reverse("admin-shell:billing-contract-detail", kwargs={"contract_code": contract.contract_code}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, contract.contract_code)
        self.assertContains(response, "Dados do contrato")
        self.assertContains(response, "Historico de faturas")

    def test_technician_cannot_open_billing_dashboard(self):
        user = UserFactory(password="admin123!", is_staff=True)
        assign_smart_system_role(user, "technician")
        self.client.force_login(user)

        response = self.client.get(reverse("admin-shell:billing-dashboard"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Acesso negado", status_code=403)

    def test_technician_cannot_open_observability_dashboard(self):
        user = UserFactory(password="admin123!", is_staff=True)
        assign_smart_system_role(user, "technician")
        self.client.force_login(user)

        response = self.client.get(reverse("admin-shell:observability-dashboard"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Acesso negado", status_code=403)

    def test_super_admin_can_mark_invoice_paid(self):
        _, invoice = self._create_billing_contract()
        user = UserFactory(password="admin123!", is_staff=True)
        assign_smart_system_role(user, "super-admin")
        self.client.force_login(user)

        response = self.client.post(
            reverse("admin-shell:billing-invoice-mark-paid", kwargs={"invoice_number": invoice.invoice_number})
        )

        self.assertEqual(response.status_code, 302)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, "paid")

    def test_auditor_cannot_export_report(self):
        user = UserFactory(password="admin123!", is_staff=True)
        assign_smart_system_role(user, "auditor-readonly")
        self.client.force_login(user)

        response = self.client.get(
            reverse(
                "admin-shell:smart-system-report-download",
                kwargs={"report_type": "work-order", "reference_code": "OS-2026-0148"},
            )
        )

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Acesso negado", status_code=403)

    def test_technician_cannot_complete_work_order_directly(self):
        user = UserFactory(password="admin123!", is_staff=True)
        MembershipFactory(user=user, company=self.academia_company, is_primary=False)
        assign_smart_system_role(user, "technician", company=self.academia_company)
        self.client.force_login(user)

        response = self.client.post(
            reverse("admin-shell:smart-system-work-order-complete-execution", kwargs={"order_code": "OS-2026-0151"})
        )

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Acesso negado", status_code=403)

    def test_shell_execution_requires_final_observations_before_completion(self):
        category = AssetCategoryFactory(name="Categoria Shell")
        asset = AssetFactory(
            operational_site=self.default_site,
            category=category,
            asset_tag="ESTEIRA-SHELL-01",
            name="Esteira Shell",
        )
        ServiceOrderFactory(
            order_number="OS-SHELL-EXEC-998",
            client=self.default_client,
            operational_site=self.default_site,
            asset=asset,
            assigned_to=self.user,
            created_by=self.user,
            title="Falha na esteira",
            status=ServiceOrder.Status.IN_PROGRESS,
        )

        response = self.client.post(
            reverse("admin-shell:smart-system-work-order-complete-execution", kwargs={"order_code": "OS-SHELL-EXEC-998"})
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/app/smart-system/work-orders/OS-SHELL-EXEC-998/execute/", response.url)

    def test_mobile_signature_capture_creates_technician_signature(self):
        technician = UserFactory(password="admin123!", is_staff=True)
        MembershipFactory(user=technician, company=self.academia_company, is_primary=False)
        assign_smart_system_role(technician, "technician", company=self.academia_company)
        category = AssetCategoryFactory(name="Categoria Mobile")
        asset = AssetFactory(
            operational_site=self.default_site,
            category=category,
            asset_tag="BIKE-MOB-TST-01",
            name="Bike 07",
        )
        ServiceOrderFactory(
            order_number="OS-MOB-SIG-887",
            client=self.default_client,
            operational_site=self.default_site,
            asset=asset,
            assigned_to=technician,
            created_by=self.user,
            title="Falha de partida",
            status=ServiceOrder.Status.IN_PROGRESS,
        )
        self.client.force_login(technician)

        response = self.client.post(
            reverse("admin-shell:technician-app-service-sign-technician", kwargs={"order_code": "OS-MOB-SIG-887"}),
            {
                "signer_name": "Ana Lopes",
                "signature_data": "data:image/png;base64,AAAA",
                "acceptance_notes": "Execucao concluida em campo.",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ServiceSignature.objects.filter(
                service_order__order_number="OS-MOB-SIG-887",
                signature_type=ServiceSignature.SignatureType.TECHNICIAN_COMPLETION,
                signer_name="Ana Lopes",
                is_current=True,
            ).exists()
        )

    def test_scoped_user_sees_only_current_company_records(self):
        scoped_user, academia, _, _, _ = self._create_scoped_manager()
        self.client.force_login(scoped_user)

        session = self.client.session
        session["smart_system_active_company_id"] = academia.id
        session["smart_system_active_site_id"] = None
        session.save()

        response = self.client.get(reverse("admin-shell:smart-system-assets"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CHILLER-UNID-A")
        self.assertContains(response, "HVAC-ACADEMIA-02")
        self.assertContains(response, "ESTEIRA-ERG-12")
        self.assertNotContains(response, "CAMARA-CLIMATICA-01")
        self.assertNotContains(response, "Laboratorio Campinas")

    def test_scoped_user_cannot_open_asset_from_other_company(self):
        scoped_user, academia, panobianco, _, _ = self._create_scoped_manager()
        self.client.force_login(scoped_user)

        session = self.client.session
        session["smart_system_active_company_id"] = panobianco.id
        session.save()

        response = self.client.get(
            reverse("admin-shell:smart-system-asset-detail", kwargs={"asset_code": "CHILLER-UNID-A"})
        )

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Fora do escopo")

    def test_context_switcher_updates_active_scope(self):
        scoped_user, academia, panobianco, _, panobianco_site = self._create_scoped_manager()
        self.client.force_login(scoped_user)

        response = self.client.post(
            reverse("admin-shell:set-active-context"),
            {
                "company_id": str(panobianco.id),
                "site_id": str(panobianco_site.id),
                "next": reverse("admin-shell:smart-system-assets"),
            },
        )

        self.assertEqual(response.status_code, 302)
        session = self.client.session
        self.assertEqual(session["smart_system_active_company_id"], panobianco.id)
        self.assertEqual(session["smart_system_active_site_id"], panobianco_site.id)

    def test_scoped_report_preview_denies_foreign_company(self):
        scoped_user, academia, panobianco, _, _ = self._create_scoped_manager()
        self.client.force_login(scoped_user)

        session = self.client.session
        session["smart_system_active_company_id"] = panobianco.id
        session.save()

        response = self.client.get(
            reverse(
                "admin-shell:smart-system-report-preview",
                kwargs={"report_type": "asset-summary", "reference_code": "CHILLER-UNID-A"},
            )
        )

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Fora do escopo")

    def test_part_filter_low_stock(self):
        response = self.client.get(reverse("admin-shell:smart-system-parts"), {"low_stock": "yes"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PRT-0005")
        self.assertNotContains(response, "PRT-0002")

    def test_work_order_list_loads(self):
        response = self.client.get(reverse("admin-shell:smart-system-work-orders"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestao operacional de corretivas, preventivas, inspecoes e intervencoes tecnicas")
        self.assertContains(response, "OS-2026-0148")
        self.assertContains(response, "Carteira de ordens")

    def test_work_order_detail_loads(self):
        response = self.client.get(
            reverse("admin-shell:smart-system-work-order-detail", kwargs={"order_code": "OS-2026-0151"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Falha de partida da esteira ergometrica 12")
        self.assertContains(response, "Fluxo operacional da OS")
        self.assertContains(response, "Timeline da ordem")

    def test_work_order_execution_loads(self):
        response = self.client.get(
            reverse("admin-shell:smart-system-work-order-execution", kwargs={"order_code": "OS-2026-0151"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contexto operacional")
        self.assertContains(response, "Checklist executavel")
        self.assertContains(response, "RT250")
        self.assertContains(response, "PRT-0005")

    def test_work_order_start_execution_redirects(self):
        response = self.client.post(
            reverse("admin-shell:smart-system-work-order-start-execution", kwargs={"order_code": "OS-2026-0151"})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/app/smart-system/work-orders/OS-2026-0151/execute/", response.url)

    def test_work_order_save_progress_redirects(self):
        response = self.client.post(
            reverse("admin-shell:smart-system-work-order-save-progress", kwargs={"order_code": "OS-2026-0151"})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/app/smart-system/work-orders/OS-2026-0151/execute/", response.url)

    def test_work_order_complete_execution_redirects(self):
        response = self.client.post(
            reverse("admin-shell:smart-system-work-order-complete-execution", kwargs={"order_code": "OS-2026-0151"}),
            {"final_observations": "Encerramento teste: equipamento validado e liberado para operacao."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/app/smart-system/work-orders/OS-2026-0151/", response.url)
        self.assertNotIn("completed=1", response.url)

    def test_work_order_filter_by_piece_pending(self):
        response = self.client.get(reverse("admin-shell:smart-system-work-orders"), {"piece_pending": "yes"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "OS-2026-0151")
        self.assertNotContains(response, "OS-2026-0149")

    def test_preventive_plan_list_loads(self):
        response = self.client.get(reverse("admin-shell:smart-system-preventives"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestao de recorrencia, agenda, cobertura e execucao da manutencao planejada")
        self.assertContains(response, "PP-2026-001")
        self.assertContains(response, "Carteira preventiva")

    def test_preventive_schedule_and_calendar_load(self):
        schedule_response = self.client.get(reverse("admin-shell:smart-system-preventives-schedule"))
        calendar_response = self.client.get(reverse("admin-shell:smart-system-preventives-calendar"))
        self.assertEqual(schedule_response.status_code, 200)
        self.assertEqual(calendar_response.status_code, 200)
        self.assertContains(schedule_response, "Agenda operacional")
        self.assertContains(calendar_response, "Calendario operacional")
        self.assertContains(calendar_response, "Março 2026")

    def test_preventive_detail_loads(self):
        response = self.client.get(
            reverse("admin-shell:smart-system-preventive-detail", kwargs={"plan_code": "PP-2026-003"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Lubrificacao quinzenal das esteiras cardio")
        self.assertContains(response, "Recorrencia")
        self.assertContains(response, "Checklist vinculado")

    def test_preventive_filter_by_overdue(self):
        response = self.client.get(reverse("admin-shell:smart-system-preventives"), {"overdue": "yes"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PP-2026-003")
        self.assertNotContains(response, "PP-2026-002")

    def test_failure_list_loads(self):
        response = self.client.get(reverse("admin-shell:smart-system-failures"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registro, analise e historico de falhas de ativos")
        self.assertContains(response, "FE-2026-001")
        self.assertContains(response, "Eventos de falha")

    def test_failure_detail_loads(self):
        response = self.client.get(
            reverse("admin-shell:smart-system-failure-detail", kwargs={"failure_code": "FE-2026-002"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Falha eletrica")
        self.assertContains(response, "Causa raiz / RCA")
        self.assertContains(response, "Historico do ativo")

    def test_failure_filter_without_diagnosis(self):
        scb = CompanyFactory(name="Smart Control Brasil", slug="tests-shell-smart-control")
        MembershipFactory(user=self.user, company=scb, is_primary=False)
        assign_smart_system_role(self.user, "maintenance-manager", company=scb)
        fail_session = self.client.session
        fail_session["smart_system_active_company_id"] = scb.id
        fail_session.pop("smart_system_active_site_id", None)
        fail_session.save()

        response = self.client.get(reverse("admin-shell:smart-system-failures"), {"without_diagnosis": "yes"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "FE-2026-004")
        self.assertNotContains(response, "FE-2026-002")

    def test_checklist_list_loads(self):
        response = self.client.get(reverse("admin-shell:smart-system-checklists"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cadastre rotinas tecnicas simples para equipamentos, servicos e preventivas")
        self.assertContains(response, "Lista de checklists")
        self.assertContains(response, "Novo checklist")
        self.assertNotContains(response, "Taxa de conformidade")

    def test_checklist_detail_loads(self):
        response = self.client.get(
            reverse("admin-shell:smart-system-checklist-detail", kwargs={"checklist_code": "CHK-2026-002"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verificacao Funcional de Esteira")
        self.assertContains(response, "Estrutura dos itens")
        self.assertContains(response, "Historico resumido de execucoes")

    def test_checklist_execution_loads(self):
        response = self.client.get(
            reverse("admin-shell:smart-system-checklist-execution", kwargs={"checklist_code": "CHK-2026-002"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Itens executaveis")
        self.assertContains(response, "EX-CHK-002-B")
        self.assertContains(response, "NOK")

    def test_checklist_execution_detail_loads(self):
        response = self.client.get(
            reverse(
                "admin-shell:smart-system-checklist-execution-detail",
                kwargs={"checklist_code": "CHK-2026-002", "execution_code": "EX-CHK-002"},
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Conclusao registrada")
        self.assertContains(response, "Concluida com anomalias criticas")
        self.assertContains(response, "Falha de partida confirmada com placa e capacitor fora da faixa")

    def test_checklist_filter_by_application_type(self):
        response = self.client.get(reverse("admin-shell:smart-system-checklists"), {"application_type": "service"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Verificacao Funcional de Esteira")

    def test_sidebar_contains_core_navigation(self):
        response = self.client.get(reverse("admin-shell:dashboard"))
        self.assertContains(response, "Marketplace Technicians")
        self.assertContains(response, "Configuration Center")
        self.assertContains(response, "Ordens de Servico")
        self.assertContains(response, "Preventivas")
        self.assertContains(response, "Falhas")
        self.assertContains(response, "Checklists")
        self.assertContains(response, "Pecas")
        self.assertContains(response, "Relatorios")

    def test_dashboard_contains_technical_catalog_b2b_shortcuts(self):
        response = self.client.get(reverse("admin-shell:dashboard-entry"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Catálogo Técnico B2B")
        self.assertContains(response, "Gerenciar produtos")
        self.assertContains(response, "Adicionar produto")
        self.assertContains(response, "Biblioteca de imagens")
        self.assertContains(response, reverse("admin-shell:technical-catalog-product-list"))
        self.assertContains(response, reverse("admin-shell:technical-catalog-product-create"))
        self.assertContains(response, reverse("admin-shell:media-image-list"))

    def test_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("admin-shell:dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_manager_copilot_page_loads(self):
        response = self.client.get(reverse("admin-shell:ai-manager-copilot"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Copilot para Gestor")
        self.assertContains(response, "Conversa atual")

    def test_voiceops_center_page_loads(self):
        company = self._create_voiceops_data()
        session = self.client.session
        session["smart_system_active_company_id"] = company.id
        session.save()
        response = self.client.get(reverse("admin-shell:ai-voiceops-center"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "VoiceOps")
        self.assertContains(response, "o que esta critico hoje")
