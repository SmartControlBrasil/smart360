import json

from django.test import TestCase, override_settings
from django.urls import reverse

from ..models import Lead, LeadInteraction, LeadSource


@override_settings(SMART360_LIVIA_M2M_TOKEN="secure-livia-token")
class LiviaLeadIngestApiTests(TestCase):
    URL = reverse("growth-livia-leads-ingest")

    def _payload(self, **overrides):
        payload = {
            "tenant_slug": "smart-control-brasil",
            "name": "Maria",
            "company": "ACME",
            "email": "maria@acme.com",
            "phone": "11999998888",
            "city": "São Paulo",
            "need_summary": "Preciso de automação industrial.",
            "source_page": "https://example.com/livia",
            "conversation_id": "conv-123",
        }
        payload.update(overrides)
        return payload

    def _post(self, payload, token="secure-livia-token"):
        return self.client.post(
            self.URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )

    def test_missing_token_returns_401(self):
        response = self.client.post(
            self.URL,
            data=json.dumps(self._payload()),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(Lead.objects.count(), 0)

    def test_invalid_token_returns_401(self):
        response = self._post(self._payload(), token="invalid-token")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(Lead.objects.count(), 0)

    def test_valid_payload_creates_lead(self):
        response = self._post(self._payload())

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertTrue(body["created"])
        self.assertEqual(Lead.objects.count(), 1)
        lead = Lead.objects.first()
        self.assertEqual(lead.company_name, "ACME")
        self.assertEqual(lead.contact_name, "Maria")
        self.assertEqual(lead.metadata.get("origin"), "livia_platform")
        self.assertEqual(LeadSource.objects.filter(name="Lívia Platform").count(), 1)
        self.assertEqual(LeadInteraction.objects.count(), 1)
        interaction = LeadInteraction.objects.first()
        self.assertIn("Preciso de automação industrial.", interaction.summary)
        self.assertIn("conversation_id", interaction.summary.lower())

    def test_repeated_email_updates_without_duplication(self):
        first = self._post(self._payload())
        self.assertEqual(first.status_code, 201)

        second_payload = self._payload(
            company="ACME Atualizada",
            city="Campinas",
        )
        second = self._post(second_payload)

        self.assertEqual(second.status_code, 200)
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(LeadInteraction.objects.count(), 2)
        lead = Lead.objects.first()
        self.assertEqual(lead.company_name, "ACME")
        self.assertEqual(lead.city, "São Paulo")

    def test_repeated_phone_updates_without_duplication(self):
        first_payload = self._payload(email="", phone="11999998888")
        first = self._post(first_payload)
        self.assertEqual(first.status_code, 201)

        second_payload = self._payload(
            email="",
            phone="11999998888",
            company="ACME Nova",
        )
        second = self._post(second_payload)

        self.assertEqual(second.status_code, 200)
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(LeadInteraction.objects.count(), 2)

    def test_payload_without_name_or_company_is_rejected(self):
        response = self._post(self._payload(name="", company=""))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Lead.objects.count(), 0)
