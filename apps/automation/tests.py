import json
from django.test import TestCase
from django.db import IntegrityError
from django.urls import reverse

from .models import AutomationEvent, AutomationLog, WebhookEndpoint
from apps.growth_engine.models import Lead


class AutomationModelsTests(TestCase):
    def test_create_automation_log(self):
        log = AutomationLog.objects.create(
            source="n8n",
            workflow_name="lead-routing",
            event_type="lead.created",
            status=AutomationLog.Status.PENDING,
            payload={"lead_id": 10},
        )
        self.assertEqual(log.source, "n8n")
        self.assertEqual(log.status, AutomationLog.Status.PENDING)
        self.assertEqual(log.payload["lead_id"], 10)

    def test_create_automation_event(self):
        event = AutomationEvent.objects.create(
            event_type="maintenance.alert",
            source="smart_system",
            payload={"asset_id": 99},
        )
        self.assertFalse(event.processed)
        self.assertEqual(event.source, "smart_system")
        self.assertEqual(event.payload["asset_id"], 99)

    def test_create_webhook_endpoint(self):
        endpoint = WebhookEndpoint.objects.create(
            name="N8N Lead Webhook",
            slug="n8n-lead-webhook",
            is_active=True,
            secret_token="top-secret",
        )
        self.assertEqual(endpoint.name, "N8N Lead Webhook")
        self.assertTrue(endpoint.is_active)
        self.assertEqual(endpoint.slug, "n8n-lead-webhook")

    def test_webhook_endpoint_slug_is_unique(self):
        WebhookEndpoint.objects.create(name="Webhook A", slug="webhook-a")
        with self.assertRaises(IntegrityError):
            WebhookEndpoint.objects.create(name="Webhook B", slug="webhook-a")


class AutomationWebhookViewTests(TestCase):
    def _url(self, slug, token=None):
        url = reverse("automation:automation_webhook_receive", kwargs={"slug": slug})
        if token:
            return f"{url}?token={token}"
        return url

    def test_post_valid_creates_event_and_log(self):
        endpoint = WebhookEndpoint.objects.create(name="N8N", slug="n8n-hook", is_active=True)
        response = self.client.post(
            self._url(endpoint.slug),
            data=json.dumps({"event_type": "lead.created", "source": "n8n", "payload": {"id": 1}}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(AutomationEvent.objects.count(), 1)
        self.assertEqual(AutomationLog.objects.count(), 1)
        self.assertEqual(AutomationLog.objects.first().status, AutomationLog.Status.SUCCESS)
        self.assertEqual(Lead.objects.count(), 1)

    def test_get_returns_method_not_allowed(self):
        endpoint = WebhookEndpoint.objects.create(name="N8N", slug="get-not-allowed", is_active=True)
        response = self.client.get(self._url(endpoint.slug))
        self.assertEqual(response.status_code, 405)

    def test_missing_slug_returns_404(self):
        response = self.client.post(
            self._url("missing"),
            data=json.dumps({"event_type": "x"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_inactive_endpoint_returns_403(self):
        endpoint = WebhookEndpoint.objects.create(name="Inactive", slug="inactive", is_active=False)
        response = self.client.post(
            self._url(endpoint.slug),
            data=json.dumps({"event_type": "x"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_secret_token_is_required(self):
        endpoint = WebhookEndpoint.objects.create(
            name="Secured",
            slug="secured",
            is_active=True,
            secret_token="expected-token",
        )
        response = self.client.post(
            self._url(endpoint.slug),
            data=json.dumps({"event_type": "x"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_secret_token_accepts_header(self):
        endpoint = WebhookEndpoint.objects.create(
            name="Secured Header",
            slug="secured-header",
            is_active=True,
            secret_token="expected-token",
        )
        response = self.client.post(
            self._url(endpoint.slug),
            data=json.dumps({"event_type": "ok"}),
            content_type="application/json",
            HTTP_X_AUTOMATION_TOKEN="expected-token",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AutomationEvent.objects.count(), 1)

    def test_invalid_json_returns_400_and_creates_failed_log(self):
        endpoint = WebhookEndpoint.objects.create(name="Invalid Json", slug="invalid-json", is_active=True)
        response = self.client.post(
            self._url(endpoint.slug),
            data='{"event_type": "broken"',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AutomationEvent.objects.count(), 0)
        self.assertEqual(AutomationLog.objects.count(), 1)
        log = AutomationLog.objects.first()
        self.assertEqual(log.status, AutomationLog.Status.FAILED)
        self.assertEqual(log.event_type, "invalid_json")

    def test_xyron_lead_event_creates_event_log_and_lead(self):
        endpoint = WebhookEndpoint.objects.create(name="Xyron Hook", slug="xyron-hook", is_active=True)
        response = self.client.post(
            self._url(endpoint.slug),
            data=json.dumps(
                {
                    "event_type": "xyron.lead.created",
                    "source": "n8n",
                    "company_name": "APAE Exemplo",
                    "contact_name": "Maria",
                    "email": "contato@apaeexemplo.org.br",
                    "whatsapp": "14999999999",
                    "city": "Marília",
                    "state": "SP",
                    "segment": "APAE",
                    "product_interest": "LIRO",
                    "message": "Lead capturado para campanha Xyron LIRO",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AutomationEvent.objects.count(), 1)
        self.assertEqual(AutomationLog.objects.count(), 1)
        self.assertEqual(Lead.objects.count(), 1)
        lead = Lead.objects.first()
        self.assertEqual(lead.company_name, "APAE Exemplo")
        self.assertEqual(lead.email, "contato@apaeexemplo.org.br")
        self.assertEqual(lead.metadata.get("product_interest"), "LIRO")
        log = AutomationLog.objects.first()
        self.assertEqual(log.response.get("lead_id"), lead.id)
        self.assertTrue(log.response.get("lead_created"))

    def test_same_email_does_not_duplicate_lead(self):
        endpoint = WebhookEndpoint.objects.create(name="Xyron Hook 2", slug="xyron-hook-2", is_active=True)
        payload = {
            "event_type": "xyron.lead.created",
            "source": "n8n",
            "company_name": "APAE Exemplo",
            "contact_name": "Maria",
            "email": "contato@apaeexemplo.org.br",
            "whatsapp": "14999999999",
            "city": "Marília",
            "state": "SP",
            "segment": "APAE",
            "product_interest": "LIRO",
            "message": "Lead capturado para campanha Xyron LIRO",
        }
        first = self.client.post(self._url(endpoint.slug), data=json.dumps(payload), content_type="application/json")
        self.assertEqual(first.status_code, 200)
        payload["message"] = "Atualização do mesmo lead"
        second = self.client.post(self._url(endpoint.slug), data=json.dumps(payload), content_type="application/json")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Lead.objects.count(), 1)
        self.assertFalse(AutomationLog.objects.order_by("-id").first().response.get("lead_created"))

    def test_without_email_uses_whatsapp_or_phone_to_avoid_duplicate(self):
        endpoint = WebhookEndpoint.objects.create(name="Xyron Hook 3", slug="xyron-hook-3", is_active=True)
        base_payload = {
            "event_type": "xyron.lead.created",
            "source": "n8n",
            "company_name": "Academia Exemplo",
            "contact_name": "João",
            "email": "",
            "whatsapp": "(14) 99999-9999",
            "city": "Bauru",
            "state": "SP",
            "segment": "Academia",
            "product_interest": "HygiBot",
            "message": "Primeiro contato",
        }
        first = self.client.post(self._url(endpoint.slug), data=json.dumps(base_payload), content_type="application/json")
        self.assertEqual(first.status_code, 200)
        second_payload = {**base_payload, "message": "Segundo contato"}
        second = self.client.post(self._url(endpoint.slug), data=json.dumps(second_payload), content_type="application/json")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Lead.objects.count(), 1)

    def test_product_interest_liro_is_saved(self):
        endpoint = WebhookEndpoint.objects.create(name="Xyron Hook 4", slug="xyron-hook-4", is_active=True)
        response = self.client.post(
            self._url(endpoint.slug),
            data=json.dumps(
                {
                    "event_type": "xyron.lead.created",
                    "source": "n8n",
                    "company_name": "APAE Exemplo",
                    "product_interest": "LIRO",
                    "message": "Interesse em LIRO para educação",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        lead = Lead.objects.first()
        self.assertEqual(lead.metadata.get("product_interest"), "LIRO")
        self.assertIn("Interesse de produto: LIRO", lead.notes)

    def test_non_lead_event_does_not_create_lead(self):
        endpoint = WebhookEndpoint.objects.create(name="Ops Hook", slug="ops-hook", is_active=True)
        response = self.client.post(
            self._url(endpoint.slug),
            data=json.dumps({"event_type": "machine.alert", "source": "n8n", "machine_id": 10}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AutomationEvent.objects.count(), 1)
        self.assertEqual(AutomationLog.objects.count(), 1)
        self.assertEqual(Lead.objects.count(), 0)
