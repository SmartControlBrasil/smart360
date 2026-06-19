import json
from decimal import Decimal

from django.test import TestCase

from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.ai_agents_center.models import AgentActionProposal, CommercialOpportunity
from apps.ai_agents_center.services.commercial_intelligence import CommercialIntelligenceService
from apps.ai_agents_center.services.opportunity_builder import OpportunityBuilderService
from apps.ai_agents_center.services.orchestrator import AgentCoordinatorService
from apps.ai_agents_center.services.registry import AgentRegistryService
from apps.growth_engine.models import Lead
from tests.factories.core import CompanyFactory, MembershipFactory, UserFactory


class EduardoCommercialOpportunityTests(TestCase):
    def setUp(self):
        bootstrap_smart_system_access()
        AgentRegistryService.bootstrap_registry()
        self.user = UserFactory(email="edu-opportunities@smart360.local", password="StrongPass123")
        self.company = CompanyFactory(name="EDU Company", slug="edu-company")
        MembershipFactory(user=self.user, company=self.company, is_primary=True)
        assign_smart_system_role(self.user, "maintenance-manager", company=self.company)

    def _analysis(self, **overrides):
        data = {
            "empresa": "Hospital Exemplo",
            "segmento": "Hospital",
            "cidade": "Sao Paulo",
            "estado": "SP",
            "site": "https://hospital.example.com.br",
            "source": "website",
            "contatos_institucionais": ["contato@hospital.example.com.br"],
            "problemas": ["alto fluxo de limpeza e higienizacao em areas comuns"],
            "evidencias": ["Site institucional informa atendimento hospitalar 24 horas"],
        }
        data.update(overrides)
        context = {"public_opportunity": CommercialIntelligenceService.normalize_opportunity(data)}
        return CommercialIntelligenceService.analyze(context=context)

    def test_builder_creates_commercial_opportunity_with_score_and_confidence(self):
        analysis = self._analysis()

        opportunity = OpportunityBuilderService.build_from_analysis(
            analysis=analysis,
            company=self.company,
            source="website",
        )

        self.assertEqual(opportunity.company_name, "Hospital Exemplo")
        self.assertEqual(opportunity.source, CommercialOpportunity.Source.WEBSITE)
        self.assertGreaterEqual(opportunity.commercial_score, 85)
        self.assertGreaterEqual(opportunity.confidence_score, Decimal("0.70"))
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.READY_FOR_REVIEW)
        self.assertIn("HygiBot", opportunity.recommended_product)


    def test_builder_prevents_duplicate_open_opportunities(self):
        analysis = self._analysis()

        first = OpportunityBuilderService.build_from_analysis(
            analysis=analysis,
            company=self.company,
            source="website",
        )
        second = OpportunityBuilderService.build_from_analysis(
            analysis=analysis,
            company=self.company,
            source="website",
        )

        self.assertEqual(first.id, second.id)
        self.assertEqual(CommercialOpportunity.objects.filter(company_name="Hospital Exemplo").count(), 1)
        self.assertTrue(second.metadata["deduplicated"])

    def test_low_confidence_opportunity_cannot_be_marked_ready_for_review(self):
        analysis = self._analysis(site="", contatos_institucionais=[], problemas=[])
        opportunity = OpportunityBuilderService.build_from_analysis(analysis=analysis, company=self.company)

        self.assertLess(opportunity.confidence_score, Decimal("0.70"))
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.ENRICHING)
        with self.assertRaises(ValueError):
            OpportunityBuilderService.mark_ready_for_review(opportunity=opportunity, user=self.user)

    def test_eduardo_run_creates_opportunity_but_does_not_create_lead(self):
        trigger_reference = json.dumps(
            {
                "empresa": "Hospital Exemplo",
                "segmento": "Hospital",
                "cidade": "Sao Paulo",
                "estado": "SP",
                "site": "https://hospital.example.com.br",
                "source": "website",
                "contatos_institucionais": ["contato@hospital.example.com.br"],
                "problemas": ["alto fluxo de limpeza e higienizacao em areas comuns"],
                "evidencias": ["Site institucional informa atendimento hospitalar 24 horas"],
            }
        )

        run = AgentCoordinatorService.run_agent(
            agent_slug="eduardo-commercial-intelligence-agent",
            company=self.company,
            triggered_by=self.user,
            trigger_reference=trigger_reference,
        )

        opportunity = CommercialOpportunity.objects.get(company_name="Hospital Exemplo")
        proposal = AgentActionProposal.objects.filter(agent_run=run).latest("created_at")
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.READY_FOR_REVIEW)
        self.assertEqual(opportunity.agent_run, run)
        self.assertEqual(proposal.action_type, "review_commercial_opportunity")
        self.assertEqual(Lead.objects.count(), 0)

    def test_manual_approval_and_conversion_to_lead(self):
        opportunity = OpportunityBuilderService.build_from_analysis(
            analysis=self._analysis(),
            company=self.company,
            source="website",
        )

        OpportunityBuilderService.approve(opportunity=opportunity, user=self.user)
        lead = OpportunityBuilderService.convert_to_lead(opportunity=opportunity, user=self.user)
        opportunity.refresh_from_db()

        self.assertEqual(opportunity.status, CommercialOpportunity.Status.CONVERTED_TO_LEAD)
        self.assertEqual(opportunity.lead, lead)
        self.assertEqual(lead.company_name, opportunity.company_name)
        self.assertEqual(lead.metadata["origin_opportunity_public_id"], str(opportunity.public_id))
        self.assertEqual(lead.metadata["opportunity_commercial_score"], opportunity.commercial_score)
