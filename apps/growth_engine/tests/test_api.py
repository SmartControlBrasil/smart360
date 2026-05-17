from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.smart_site_factory.models import Niche
from apps.users.models import User

from ..models import Lead, LeadAssignment, LeadSource, LeadTag


class GrowthEngineApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="growth@smart360.local",
            password="StrongPass123",
            first_name="Growth",
        )
        self.assignee = User.objects.create_user(
            email="sales@smart360.local",
            password="StrongPass123",
            first_name="Sales",
        )
        self.niche = Niche.objects.create(name="Advogados", slug="advogados")
        self.source = LeadSource.objects.create(name="Meta Ads", source_type=LeadSource.SourceType.PAID)
        self.tag = LeadTag.objects.create(name="Quente", slug="quente")
        self.client.force_authenticate(self.user)

    def test_create_lead_calculates_score_and_assignment(self):
        response = self.client.post(
            reverse("growth-leads-list"),
            {
                "company_name": "Acme Juridico",
                "contact_name": "Ana",
                "email": "ana@acme.com",
                "phone": "11999999999",
                "whatsapp": "11999999999",
                "website": "https://acme.com",
                "city": "Sao Paulo",
                "state": "SP",
                "niche": self.niche.id,
                "source": self.source.id,
                "assigned_to": self.assignee.id,
                "tag_ids": [self.tag.id],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lead = Lead.objects.get(company_name="Acme Juridico")
        self.assertGreater(lead.score, 0)
        self.assertEqual(lead.tags.count(), 1)
        self.assertTrue(LeadAssignment.objects.filter(lead=lead, user=self.assignee).exists())

    def test_assign_endpoint_creates_assignment(self):
        lead = Lead.objects.create(company_name="Lead Teste", created_by=self.user)
        response = self.client.post(reverse("growth-leads-assign", kwargs={"pk": lead.pk}), {"user": self.assignee.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        lead.refresh_from_db()
        self.assertEqual(lead.assigned_to, self.assignee)
