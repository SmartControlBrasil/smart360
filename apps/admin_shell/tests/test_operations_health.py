from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from apps.ai_agents_center.models import (
    AgentActionProposal,
    AgentAssetAttentionFlag,
    AgentDefinition,
    AgentRecommendation,
    AgentRun,
    AgentScheduleHealthFlag,
)
from apps.companies.models import Company, Membership, SiteMembership
from apps.smart_system.models import Asset, AssetCategory, MaintenanceClient, OperationalSite
from apps.admin_shell.views import OperationsHealthView


class OperationsHealthViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="ops-health@smart360.local",
            password="StrongPass123",
            first_name="Ops",
            is_staff=True,
        )
        self.company = Company.objects.create(name="Operação Cliente", slug="operacao-cliente")
        self.client_model = MaintenanceClient.objects.create(company=self.company, display_name="Operação Cliente")
        self.site = OperationalSite.objects.create(maintenance_client=self.client_model, name="Unidade Operacional")
        self.category = AssetCategory.objects.create(name="Operação HVAC", slug="operacao-hvac")
        self.asset = Asset.objects.create(
            operational_site=self.site,
            category=self.category,
            asset_tag="OPS-001",
            name="Chiller Operacional",
        )
        Membership.objects.create(user=self.user, company=self.company, status=Membership.Status.ACTIVE, is_primary=True)
        SiteMembership.objects.create(user=self.user, company=self.company, site=self.site, status=SiteMembership.Status.ACTIVE, is_primary=True)
        self.client.force_login(self.user)

    def create_agent_data(self):
        maintenance_agent = AgentDefinition.objects.create(
            slug="maintenance-agent",
            name="Maintenance Agent",
            domain=AgentDefinition.Domain.MAINTENANCE,
            status=AgentDefinition.Status.ACTIVE,
            enabled=True,
        )
        scheduling_agent = AgentDefinition.objects.create(
            slug="scheduling-agent",
            name="Scheduling Agent",
            domain=AgentDefinition.Domain.SCHEDULING,
            status=AgentDefinition.Status.ACTIVE,
            enabled=True,
        )
        maintenance_run = AgentRun.objects.create(
            agent=maintenance_agent,
            company=self.company,
            site=self.site,
            trigger_type=AgentRun.TriggerType.SCHEDULED,
            status=AgentRun.Status.COMPLETED,
            output_summary="Ativo crítico em atenção.",
            finished_at=timezone.now(),
        )
        scheduling_run = AgentRun.objects.create(
            agent=scheduling_agent,
            company=self.company,
            site=self.site,
            trigger_type=AgentRun.TriggerType.MANUAL,
            status=AgentRun.Status.COMPLETED,
            output_summary="Agenda com risco de SLA.",
            finished_at=timezone.now(),
        )
        recommendation = AgentRecommendation.objects.create(
            agent_run=maintenance_run,
            company=self.company,
            site=self.site,
            recommendation_type=AgentRecommendation.RecommendationType.CRITICAL_ASSET_WATCH,
            title="Inspecionar chiller crítico",
            summary="Vibração acima do padrão nos últimos atendimentos.",
            severity=AgentRecommendation.Severity.HIGH,
            priority=AgentRecommendation.Priority.HIGH,
            status=AgentRecommendation.Status.OPEN,
            attention_score=88,
        )
        AgentActionProposal.objects.create(
            agent_run=scheduling_run,
            action_type="reschedule_visit",
            title="Reorganizar agenda técnica",
            summary="Mover visita para reduzir risco de SLA.",
            priority="high",
            status=AgentActionProposal.Status.PENDING_APPROVAL,
        )
        AgentAssetAttentionFlag.objects.create(
            agent=maintenance_agent,
            company=self.company,
            site=self.site,
            asset=self.asset,
            latest_run=maintenance_run,
            latest_recommendation=recommendation,
            status=AgentAssetAttentionFlag.Status.ACTIVE,
            attention_score=91,
            summary="Chiller com risco operacional elevado.",
            risk_level="high",
        )
        AgentScheduleHealthFlag.objects.create(
            agent=scheduling_agent,
            company=self.company,
            site=self.site,
            technician=self.user,
            latest_run=scheduling_run,
            status=AgentScheduleHealthFlag.Status.WATCHING,
            attention_score=77,
            summary="Agenda com sobrecarga no período da tarde.",
            risk_level="medium",
            flag_type=AgentScheduleHealthFlag.FlagType.TECHNICIAN_OVERLOAD,
            schedule_date=timezone.localdate(),
        )

    def test_operations_health_url_resolves_to_view(self):
        resolved = resolve("/app/operations/health/")

        self.assertIs(resolved.func.view_class, OperationsHealthView)

    def test_operations_health_page_loads_with_template(self):
        response = self.client.get(reverse("admin-shell:operations-health"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin_shell/operations_health.html")
        self.assertContains(response, "Operação Técnica Inteligente")
        self.assertContains(response, "Riscos detectados")

    def test_operations_health_shows_real_agent_data(self):
        self.create_agent_data()

        response = self.client.get(reverse("admin-shell:operations-health"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inspecionar chiller crítico")
        self.assertContains(response, "Reorganizar agenda técnica")
        self.assertContains(response, "Chiller com risco operacional elevado")
        self.assertContains(response, "Agenda com sobrecarga")
        self.assertContains(response, "maintenance-agent")
        self.assertContains(response, "scheduling-agent")
        self.assertContains(response, reverse("admin-shell:ai-agents-recommendations"))
        self.assertContains(response, reverse("admin-shell:ai-agents-proposals"))
