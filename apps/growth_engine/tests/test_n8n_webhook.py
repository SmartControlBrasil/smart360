import json

from django.test import TestCase, override_settings

from apps.growth_engine.models import Lead


@override_settings(N8N_WEBHOOK_TOKEN="token-seguro")
class N8NWebhookLeadTests(TestCase):
    URL = "/api/integrations/n8n/leads/"

    def _payload(self):
        return {
            "name": "Maria",
            "company": "APAE Exemplo",
            "segment": "Educação",
            "city": "Marília",
            "state": "SP",
            "phone": "14999999999",
            "email": "contato@apaeexemplo.org.br",
            "interest": "LIRO",
            "source": "n8n",
            "notes": "Lead de campanha institucional",
        }

    def test_create_with_valid_token(self):
        response = self.client.post(
            self.URL,
            data=json.dumps(self._payload()),
            content_type="application/json",
            HTTP_X_N8N_TOKEN="token-seguro",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertTrue(body["created"])
        self.assertFalse(body["duplicate"])
        self.assertEqual(Lead.objects.count(), 1)
        lead = Lead.objects.first()
        self.assertEqual(lead.company_name, "APAE Exemplo")
        self.assertEqual(lead.contact_name, "Maria")
        self.assertEqual(lead.email, "contato@apaeexemplo.org.br")
        self.assertEqual(lead.metadata.get("interest"), "LIRO")

    def test_same_email_and_source_returns_duplicate_without_creating(self):
        payload = self._payload()
        first = self.client.post(
            self.URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_N8N_TOKEN="token-seguro",
        )
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            self.URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_N8N_TOKEN="token-seguro",
        )
        self.assertEqual(second.status_code, 200)
        second_body = second.json()
        self.assertTrue(second_body["ok"])
        self.assertFalse(second_body["created"])
        self.assertTrue(second_body["duplicate"])
        self.assertEqual(Lead.objects.count(), 1)

    def test_same_phone_and_source_without_email_returns_duplicate_without_creating(self):
        payload = self._payload()
        payload["email"] = ""
        first = self.client.post(
            self.URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_N8N_TOKEN="token-seguro",
        )
        self.assertEqual(first.status_code, 201)

        second = self.client.post(
            self.URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_N8N_TOKEN="token-seguro",
        )
        self.assertEqual(second.status_code, 200)
        second_body = second.json()
        self.assertFalse(second_body["created"])
        self.assertTrue(second_body["duplicate"])
        self.assertEqual(Lead.objects.count(), 1)

    def test_different_source_allows_new_lead(self):
        payload = self._payload()
        first = self.client.post(
            self.URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_N8N_TOKEN="token-seguro",
        )
        self.assertEqual(first.status_code, 201)

        payload["source"] = "n8n-alt"
        second = self.client.post(
            self.URL,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_N8N_TOKEN="token-seguro",
        )
        self.assertEqual(second.status_code, 201)
        self.assertEqual(Lead.objects.count(), 2)

    def test_error_without_token(self):
        response = self.client.post(self.URL, data=json.dumps(self._payload()), content_type="application/json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Lead.objects.count(), 0)

    def test_error_with_invalid_token(self):
        response = self.client.post(
            self.URL,
            data=json.dumps(self._payload()),
            content_type="application/json",
            HTTP_X_N8N_TOKEN="token-incorreto",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Lead.objects.count(), 0)

    def test_error_with_invalid_minimal_payload(self):
        response = self.client.post(
            self.URL,
            data=json.dumps({"source": "n8n"}),
            content_type="application/json",
            HTTP_X_N8N_TOKEN="token-seguro",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Lead.objects.count(), 0)
