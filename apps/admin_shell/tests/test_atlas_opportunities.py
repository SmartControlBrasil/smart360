from decimal import Decimal
import inspect

from django.test import TestCase
from django.urls import reverse

from apps.admin_shell.views import AtlasCommercialOpportunityActionView, AtlasCommercialOpportunityListView
from apps.ai_agents_center.models import CommercialOpportunity
from apps.growth_engine.models import Lead
from tests.factories.core import CompanyFactory, UserFactory


class AdminShellAtlasOpportunityTests(TestCase):
    def setUp(self):
        self.user = UserFactory(email="atlas-shell@smart360.local", password="StrongPass123", is_staff=True, is_superuser=True)
        self.company = CompanyFactory(name="Atlas Shell Company", slug="atlas-shell-company")
        self.client.force_login(self.user)

    def _opportunity(self, **overrides):
        defaults = {
            "company": self.company,
            "title": "Oportunidade Atlas: Hospital Shell",
            "company_name": "Hospital Shell",
            "segment": "Hospital",
            "city": "Sao Paulo",
            "state": "SP",
            "source": CommercialOpportunity.Source.WEBSITE,
            "problem_detected": "alto fluxo de limpeza",
            "opportunity_description": "Problema detectado: alto fluxo de limpeza",
            "recommended_solution": "Robotica e integracao",
            "recommended_product": "HygiBot",
            "confidence_score": Decimal("0.82"),
            "commercial_score": 88,
            "status": CommercialOpportunity.Status.READY_FOR_REVIEW,
            "metadata": {"institutional_contacts": ["contato@hospital.test"], "website": "https://hospital.test"},
        }
        defaults.update(overrides)
        return CommercialOpportunity.objects.create(**defaults)

    def test_screen_loads_authenticated(self):
        response = self.client.get(reverse("admin-shell:atlas-opportunities"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin_shell/atlas_opportunities.html")
        self.assertContains(response, "Atlas Comercial")

    def test_lists_opportunities(self):
        self._opportunity(company_name="Clinica Atlas", segment="Clinica", city="Campinas", state="SP")

        response = self.client.get(reverse("admin-shell:atlas-opportunities"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Clinica Atlas")
        self.assertContains(response, "Clinica")
        self.assertContains(response, "Campinas/SP")
        self.assertContains(response, "88")
        self.assertContains(response, "Website")

    def test_approves_opportunity(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.NEW)

        response = self.client.post(reverse("admin-shell:atlas-opportunity-approve", kwargs={"public_id": opportunity.public_id}))

        self.assertRedirects(response, reverse("admin-shell:atlas-opportunities"))
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.APPROVED)
        self.assertEqual(opportunity.reviewed_by, self.user)

    def test_rejects_opportunity(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.READY_FOR_REVIEW)

        response = self.client.post(reverse("admin-shell:atlas-opportunity-reject", kwargs={"public_id": opportunity.public_id}))

        self.assertRedirects(response, reverse("admin-shell:atlas-opportunities"))
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.REJECTED)
        self.assertEqual(opportunity.reviewed_by, self.user)

    def test_converts_approved_opportunity_to_lead(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.APPROVED)

        response = self.client.post(reverse("admin-shell:atlas-opportunity-convert", kwargs={"public_id": opportunity.public_id}))

        self.assertRedirects(response, reverse("admin-shell:atlas-opportunities"))
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.CONVERTED_TO_LEAD)
        self.assertIsNotNone(opportunity.lead)
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(opportunity.lead.company_name, "Hospital Shell")

    def test_blocks_conversion_of_unapproved_opportunity(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.READY_FOR_REVIEW)

        response = self.client.post(reverse("admin-shell:atlas-opportunity-convert", kwargs={"public_id": opportunity.public_id}))

        self.assertRedirects(response, reverse("admin-shell:atlas-opportunities"))
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.READY_FOR_REVIEW)
        self.assertIsNone(opportunity.lead)
        self.assertEqual(Lead.objects.count(), 0)

    def test_does_not_convert_already_converted_opportunity_again(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.APPROVED)
        self.client.post(reverse("admin-shell:atlas-opportunity-convert", kwargs={"public_id": opportunity.public_id}))
        opportunity.refresh_from_db()
        lead = opportunity.lead

        response = self.client.post(reverse("admin-shell:atlas-opportunity-convert", kwargs={"public_id": opportunity.public_id}))

        self.assertRedirects(response, reverse("admin-shell:atlas-opportunities"))
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.lead, lead)
        self.assertEqual(Lead.objects.count(), 1)

    def test_new_screen_does_not_use_legacy_atlas_lead_models(self):
        sources = [
            inspect.getsource(AtlasCommercialOpportunityListView),
            inspect.getsource(AtlasCommercialOpportunityActionView),
            open("apps/admin_shell/templates/admin_shell/atlas_opportunities.html", encoding="utf-8").read(),
        ]
        combined = "\n".join(sources)

        self.assertNotIn("AtlasLead", combined)
        self.assertNotIn("PendingAtlasLead", combined)
