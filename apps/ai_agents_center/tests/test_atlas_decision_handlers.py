from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from apps.companies.models import Membership
from apps.growth_engine.models import Lead
from apps.ai_agents_center.models import CommercialOpportunity, AgentActionProposal, AgentDefinition, AgentExecutionPolicy, AgentRun
from apps.ai_agents_center.services.opportunity_builder import OpportunityBuilderService
from apps.ai_decision_engine.models import AgentDecision, DecisionPolicy
from apps.ai_decision_engine.services.orchestrator import DecisionOrchestrator
from tests.factories.core import CompanyFactory, UserFactory


class AtlasDecisionHandlersTests(TestCase):
    def setUp(self):
        self.user = UserFactory(email="atlas-decision@smart360.local", password="StrongPass123", is_staff=True, is_superuser=True)
        self.company = CompanyFactory(name="Atlas Commercial Company", slug="atlas-commercial")
        Membership.objects.create(user=self.user, company=self.company, is_primary=True)

        self.agent = AgentDefinition.objects.create(
            slug="atlas-commercial-intelligence-agent",
            name="Atlas Agent",
            domain=AgentDefinition.Domain.PLATFORM,
            status=AgentDefinition.Status.ACTIVE,
            autonomy_level=AgentDefinition.AutonomyLevel.PROPOSE,
            enabled=True,
        )
        AgentExecutionPolicy.objects.create(agent=self.agent, require_human_approval=True, allowed_action_types=["*"])

        self.run = AgentRun.objects.create(
            agent=self.agent,
            company=self.company,
            triggered_by=self.user,
            trigger_type=AgentRun.TriggerType.MANUAL,
            status=AgentRun.Status.COMPLETED,
            started_at=timezone.now(),
            finished_at=timezone.now(),
        )

    def _opportunity(self, **overrides):
        defaults = {
            "company": self.company,
            "title": "Oportunidade Atlas: Hospital",
            "company_name": "Hospital Albert",
            "segment": "Hospital",
            "city": "Sao Paulo",
            "state": "SP",
            "source": CommercialOpportunity.Source.WEBSITE,
            "problem_detected": "alto fluxo de limpeza",
            "opportunity_description": "Problema detectado: alto fluxo de limpeza",
            "recommended_solution": "Robotica e integracao",
            "recommended_product": "HygiBot",
            "confidence_score": Decimal("0.85"),
            "commercial_score": 90,
            "status": CommercialOpportunity.Status.READY_FOR_REVIEW,
            "metadata": {"institutional_contacts": ["contato@hospital.test"], "website": "https://hospital.test"},
        }
        defaults.update(overrides)
        return CommercialOpportunity.objects.create(**defaults)

    def _proposal(self, *, action_type, opportunity, payload=None, priority="medium"):
        return AgentActionProposal.objects.create(
            agent_run=self.run,
            action_type=action_type,
            target_entity="commercial_opportunity",
            target_entity_id=str(opportunity.public_id),
            title=f"Proposal {action_type}",
            summary=f"Summary for {action_type}",
            proposed_payload=payload or {"commercial_opportunity_public_id": str(opportunity.public_id)},
            priority=priority,
            approval_required=True,
        )

    def test_approve_review_commercial_opportunity_proposal(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.NEW)
        proposal = self._proposal(action_type="review_commercial_opportunity", opportunity=opportunity)

        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)
        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.AWAITING_APPROVAL)

        DecisionOrchestrator.approve_decision(decision=decision, approved_by=self.user, comment="Approved!")
        
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.APPROVED)
        self.assertEqual(opportunity.reviewed_by, self.user)

    def test_reject_review_commercial_opportunity_proposal(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.READY_FOR_REVIEW)
        proposal = self._proposal(action_type="review_commercial_opportunity", opportunity=opportunity)

        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)
        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.AWAITING_APPROVAL)

        DecisionOrchestrator.reject_decision(decision=decision, rejected_by=self.user, comment="Rejected!")

        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.REJECTED)
        self.assertEqual(opportunity.metadata["rejection_reason"], "Rejected!")

    def test_approve_convert_commercial_opportunity_to_lead_creates_lead(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.APPROVED)
        proposal = self._proposal(action_type="convert_commercial_opportunity_to_lead", opportunity=opportunity)

        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)
        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.AWAITING_APPROVAL)

        DecisionOrchestrator.approve_decision(decision=decision, approved_by=self.user, comment="Convert it!")

        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.CONVERTED_TO_LEAD)
        self.assertIsNotNone(opportunity.lead)
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(Lead.objects.first(), opportunity.lead)

    def test_convert_commercial_opportunity_to_lead_blocks_if_not_approved(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.NEW)
        proposal = self._proposal(action_type="convert_commercial_opportunity_to_lead", opportunity=opportunity)

        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)
        
        # When attempting to approve a decision whose handler raises ValueError,
        # the approval should raise ValueError or the execution fails.
        with self.assertRaises(ValueError) as ctx:
            DecisionOrchestrator.approve_decision(decision=decision, approved_by=self.user, comment="Convert it!")
        
        self.assertIn("Only APPROVED opportunities can be converted", str(ctx.exception))
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.NEW)
        self.assertIsNone(opportunity.lead)

    def test_convert_commercial_opportunity_to_lead_blocks_if_already_converted(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.APPROVED)
        lead = OpportunityBuilderService.convert_to_lead(opportunity=opportunity, user=self.user)
        opportunity.refresh_from_db()

        proposal = self._proposal(action_type="convert_commercial_opportunity_to_lead", opportunity=opportunity)
        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)

        with self.assertRaises(ValueError) as ctx:
            DecisionOrchestrator.approve_decision(decision=decision, approved_by=self.user, comment="Convert again!")

        self.assertIn("has already been converted to a lead", str(ctx.exception))
        self.assertEqual(Lead.objects.count(), 1)

    def test_enrich_commercial_opportunity_handler_execution(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.NEW)
        proposal = self._proposal(action_type="enrich_commercial_opportunity", opportunity=opportunity)

        decision = DecisionOrchestrator.receive_action_proposal(proposal=proposal)
        self.assertEqual(decision.decision_status, AgentDecision.DecisionStatus.EXECUTED)

        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.ENRICHING)
        self.assertIn("enrichment_trail", opportunity.metadata)
        self.assertEqual(Lead.objects.count(), 0)

    def test_atlas_lead_legacy_is_not_used(self):
        # Verify that CommercialOpportunity points to apps.growth_engine.models.Lead
        lead_field = CommercialOpportunity._meta.get_field("lead")
        self.assertEqual(lead_field.related_model, Lead)
        self.assertEqual(lead_field.related_model.__name__, "Lead")
        self.assertEqual(lead_field.related_model._meta.app_label, "growth_engine")

