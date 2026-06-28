from decimal import Decimal
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from django.test import RequestFactory
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.ai_agents_center.admin import CommercialOpportunityAdmin
from apps.ai_agents_center.models import CommercialOpportunity
from apps.ai_agents_center.services.opportunity_builder import OpportunityBuilderService
from apps.companies.models import Membership
from apps.growth_engine.models import Lead
from tests.factories.core import CompanyFactory, UserFactory


class AtlasOpportunityReviewApiTests(APITestCase):
    def setUp(self):
        self.user = UserFactory(email="atlas-review@smart360.local", password="StrongPass123", is_staff=True, is_superuser=True)
        self.company = CompanyFactory(name="Review Company", slug="review-company")
        Membership.objects.create(user=self.user, company=self.company, is_primary=True)
        self.client.force_authenticate(self.user)

    def _opportunity(self, **overrides):
        defaults = {
            "company": self.company,
            "title": "Oportunidade Atlas: Hospital Review",
            "company_name": "Hospital Review",
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

    def test_lists_opportunities(self):
        opportunity = self._opportunity()

        response = self.client.get(reverse("ai-agent-commercial-opportunities-list"), {"company": self.company.id})

        self.assertEqual(response.status_code, 200)
        payload = response.data["results"] if isinstance(response.data, dict) and "results" in response.data else response.data
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["public_id"], str(opportunity.public_id))
        self.assertEqual(payload[0]["company_name"], "Hospital Review")

    def test_approves_opportunity(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.NEW)

        response = self.client.post(reverse("ai-agent-commercial-opportunities-approve", kwargs={"public_id": opportunity.public_id}))

        self.assertEqual(response.status_code, 200)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.APPROVED)
        self.assertEqual(opportunity.reviewed_by, self.user)

    def test_rejects_opportunity(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.READY_FOR_REVIEW)

        response = self.client.post(
            reverse("ai-agent-commercial-opportunities-reject", kwargs={"public_id": opportunity.public_id}),
            {"reason": "Sem aderencia"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.REJECTED)
        self.assertEqual(opportunity.metadata["rejection_reason"], "Sem aderencia")

    def test_rejected_opportunity_cannot_convert_to_lead(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.REJECTED)

        response = self.client.post(reverse("ai-agent-commercial-opportunities-convert-to-lead", kwargs={"public_id": opportunity.public_id}))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Lead.objects.count(), 0)

    def test_converts_approved_opportunity_to_lead(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.APPROVED)

        response = self.client.post(reverse("ai-agent-commercial-opportunities-convert-to-lead", kwargs={"public_id": opportunity.public_id}))

        self.assertEqual(response.status_code, 200)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.CONVERTED_TO_LEAD)
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(response.data["lead_public_id"], str(opportunity.lead.public_id))

    def test_conversion_does_not_send_email_automatically(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.APPROVED)

        with patch("django.core.mail.send_mail") as send_mail_mock:
            response = self.client.post(reverse("ai-agent-commercial-opportunities-convert-to-lead", kwargs={"public_id": opportunity.public_id}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(send_mail_mock.call_count, 0)
        self.assertEqual(len(mail.outbox), 0)
        opportunity.refresh_from_db()
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.CONVERTED_TO_LEAD)
        self.assertEqual(Lead.objects.count(), 1)

    def test_converted_opportunity_cannot_convert_twice(self):
        opportunity = self._opportunity(status=CommercialOpportunity.Status.APPROVED)
        lead = OpportunityBuilderService.convert_to_lead(opportunity=opportunity, user=self.user)
        opportunity.refresh_from_db()

        response = self.client.post(reverse("ai-agent-commercial-opportunities-convert-to-lead", kwargs={"public_id": opportunity.public_id}))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(Lead.objects.first(), lead)


class AtlasOpportunityReviewAdminTests(APITestCase):
    def setUp(self):
        self.user = UserFactory(email="atlas-review-admin@smart360.local", password="StrongPass123", is_staff=True, is_superuser=True)
        self.company = CompanyFactory(name="Review Admin Company", slug="review-admin-company")
        Membership.objects.create(user=self.user, company=self.company, is_primary=True)
        self.admin = CommercialOpportunityAdmin(CommercialOpportunity, AdminSite())
        self.factory = RequestFactory()

    def _request(self):
        request = self.factory.post("/admin/ai_agents_center/commercialopportunity/")
        request.user = self.user
        setattr(request, "session", {})
        setattr(request, "_messages", FallbackStorage(request))
        return request

    def _opportunity(self, **overrides):
        defaults = {
            "company": self.company,
            "title": "Oportunidade Atlas: Admin",
            "company_name": "Admin Hospital",
            "segment": "Hospital",
            "city": "Sao Paulo",
            "state": "SP",
            "source": CommercialOpportunity.Source.MANUAL,
            "problem_detected": "limpeza intensa",
            "opportunity_description": "Problema detectado: limpeza intensa",
            "recommended_solution": "Robotica",
            "recommended_product": "HygiBot",
            "confidence_score": Decimal("0.80"),
            "commercial_score": 82,
            "status": CommercialOpportunity.Status.NEW,
            "metadata": {},
        }
        defaults.update(overrides)
        return CommercialOpportunity.objects.create(**defaults)

    def test_admin_action_does_not_convert_unapproved_opportunity(self):
        new_opportunity = self._opportunity(status=CommercialOpportunity.Status.NEW)
        approved_opportunity = self._opportunity(company_name="Approved Hospital", status=CommercialOpportunity.Status.APPROVED)

        self.admin.convert_approved_opportunities_to_lead(
            self._request(),
            CommercialOpportunity.objects.filter(id__in=[new_opportunity.id, approved_opportunity.id]),
        )

        new_opportunity.refresh_from_db()
        approved_opportunity.refresh_from_db()
        self.assertEqual(new_opportunity.status, CommercialOpportunity.Status.NEW)
        self.assertIsNone(new_opportunity.lead)
        self.assertEqual(approved_opportunity.status, CommercialOpportunity.Status.CONVERTED_TO_LEAD)
        self.assertIsNotNone(approved_opportunity.lead)
        self.assertEqual(Lead.objects.count(), 1)
