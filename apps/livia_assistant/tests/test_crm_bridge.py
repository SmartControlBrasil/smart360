import io
import json
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from apps.growth_engine.models import Lead, LeadInteraction
from apps.livia_assistant.crm_bridge import LiviaCRMBridge
from apps.livia_assistant.models import LiviaConversation, LiviaHandoffRequest, LiviaLeadCapture
from apps.livia_assistant.services import LiviaAssistantService


class LiviaCRMBridgeTests(TestCase):
    def setUp(self):
        mail.outbox.clear()
        self.conversation = LiviaConversation.objects.create(session_key="crm-session")
        self.livia_lead = LiviaLeadCapture.objects.create(
            conversation=self.conversation,
            name="Cliente Teste",
            email="cliente@example.com",
            phone="11999999999",
            company="Empresa Teste",
            city="São Paulo",
            service_interest="PMOC",
            urgency=LiviaLeadCapture.Urgency.HIGH,
            notes="quero orçamento",
            is_qualified=True,
        )

    def test_bridge_does_not_break_when_crm_is_missing(self):
        bridge = LiviaCRMBridge()
        with patch.object(bridge, "_growth_models", side_effect=ImportError):
            self.assertFalse(bridge.can_integrate())
            self.assertIsNone(bridge.create_or_update_crm_lead(self.livia_lead))

    def test_create_or_update_crm_lead_creates_growth_lead(self):
        crm_lead = LiviaCRMBridge().create_or_update_crm_lead(self.livia_lead)
        self.livia_lead.refresh_from_db()

        self.assertIsNotNone(crm_lead)
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(crm_lead.email, "cliente@example.com")
        self.assertEqual(self.livia_lead.operational_status, LiviaLeadCapture.OperationalStatus.SENT_TO_CRM)
        self.assertEqual(self.livia_lead.crm_lead_id, crm_lead.id)
        self.assertEqual(len(mail.outbox), 1)

    def test_notification_email_contains_recipients_subject_and_body(self):
        with self.settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            LIVIA_LEAD_NOTIFICATION_RECIPIENTS=["contato@smartcontrolbrasil.com.br"],
            LIVIA_LEAD_NOTIFICATION_BCC=["engenharia@smartcontrolbrasil.com.br"],
        ):
            LiviaCRMBridge().create_or_update_crm_lead(self.livia_lead)

        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ["contato@smartcontrolbrasil.com.br"])
        self.assertEqual(sent.bcc, ["engenharia@smartcontrolbrasil.com.br"])
        self.assertIn("Novo lead da Lívia - Cliente Teste", sent.subject)
        body = sent.body
        self.assertIn("Nome: Cliente Teste", body)
        self.assertIn("Empresa: Empresa Teste", body)
        self.assertIn("Telefone/WhatsApp: 11999999999", body)
        self.assertIn("E-mail: cliente@example.com", body)
        self.assertIn("Interesse/problema: quero orçamento", body)

    def test_notification_does_not_send_for_incomplete_lead(self):
        incomplete = LiviaLeadCapture.objects.create(
            conversation=self.conversation,
            name="Lead Incompleto",
            email="",
            phone="",
            company="Empresa Incompleta",
            city="São Paulo",
            service_interest="PMOC",
            notes="sem contato",
            is_qualified=False,
        )
        LiviaCRMBridge().create_or_update_crm_lead(incomplete)
        self.assertEqual(len(mail.outbox), 0)

    def test_bridge_does_not_send_or_create_when_required_and_fields_missing(self):
        incomplete_but_flagged = LiviaLeadCapture.objects.create(
            conversation=self.conversation,
            name="Lead Parcial",
            email="",
            phone="11999990000",
            company="Empresa Parcial",
            city="São Paulo",
            service_interest="PMOC",
            notes="preciso de suporte técnico",
            is_qualified=True,
        )
        result = LiviaCRMBridge().create_or_update_crm_lead(incomplete_but_flagged)
        self.assertIsNone(result)
        self.assertEqual(Lead.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_notification_is_not_duplicated_for_same_conversation(self):
        with self.settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            LiviaCRMBridge().create_or_update_crm_lead(self.livia_lead)
            second_capture = LiviaLeadCapture.objects.create(
                conversation=self.conversation,
                name="Cliente Teste 2",
                email="cliente2@example.com",
                phone="11999999998",
                company="Empresa Teste",
                city="São Paulo",
                service_interest="PMOC",
                notes="novo contato na mesma conversa",
                is_qualified=True,
            )
            LiviaCRMBridge().create_or_update_crm_lead(second_capture)

        self.assertEqual(len(mail.outbox), 1)

    def test_n8n_webhook_not_sent_when_url_empty(self):
        with self.settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            N8N_LIVIA_LEAD_WEBHOOK_URL="",
        ):
            with patch("apps.livia_assistant.crm_bridge.urlopen") as mocked_urlopen:
                LiviaCRMBridge().create_or_update_crm_lead(self.livia_lead)
        mocked_urlopen.assert_not_called()

    def test_n8n_webhook_sends_payload_and_token(self):
        with self.settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            N8N_LIVIA_LEAD_WEBHOOK_URL="https://example.com/webhook",
            N8N_LIVIA_LEAD_WEBHOOK_TOKEN="token-secret",
            N8N_LIVIA_LEAD_WEBHOOK_TIMEOUT=7,
        ):
            mocked_response = MagicMock()
            mocked_response.status = 200
            mocked_context = MagicMock()
            mocked_context.__enter__.return_value = mocked_response
            mocked_context.__exit__.return_value = False
            with patch("apps.livia_assistant.crm_bridge.urlopen", return_value=mocked_context) as mocked_urlopen:
                LiviaCRMBridge().create_or_update_crm_lead(self.livia_lead)

        mocked_urlopen.assert_called_once()
        request_obj = mocked_urlopen.call_args.args[0]
        timeout_used = mocked_urlopen.call_args.kwargs.get("timeout")
        self.assertEqual(timeout_used, 7)
        self.assertEqual(request_obj.get_header("X-smart360-token"), "token-secret")
        payload = json.loads(request_obj.data.decode("utf-8"))
        self.assertEqual(payload["event"], "livia.lead.qualified")
        self.assertEqual(payload["source"], "livia_assistant")
        self.assertEqual(payload["lead"]["contact_name"], "Cliente Teste")
        self.assertEqual(payload["lead"]["company_name"], "Empresa Teste")
        self.assertEqual(payload["lead"]["city"], "São Paulo")
        self.assertEqual(payload["lead"]["phone"], "11999999999")
        self.assertEqual(payload["lead"]["email"], "cliente@example.com")
        self.assertIn("quero orçamento", payload["lead"]["notes"])
        self.livia_lead.refresh_from_db()
        self.assertIn("n8n_livia_lead_webhook_sent_at", self.livia_lead.crm_reference)

    def test_n8n_webhook_failure_does_not_break_lead_creation(self):
        with self.settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            N8N_LIVIA_LEAD_WEBHOOK_URL="https://example.com/webhook",
        ):
            with patch("apps.livia_assistant.crm_bridge.urlopen", side_effect=TimeoutError("timeout")):
                crm_lead = LiviaCRMBridge().create_or_update_crm_lead(self.livia_lead)

        self.assertIsNotNone(crm_lead)
        self.assertEqual(Lead.objects.count(), 1)
        self.livia_lead.refresh_from_db()
        self.assertNotIn("n8n_livia_lead_webhook_sent_at", self.livia_lead.crm_reference)

    def test_n8n_webhook_not_duplicated_when_marked_sent(self):
        self.livia_lead.crm_reference = {"n8n_livia_lead_webhook_sent_at": "2026-01-01T10:00:00Z"}
        self.livia_lead.save(update_fields=["crm_reference"])
        with self.settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            N8N_LIVIA_LEAD_WEBHOOK_URL="https://example.com/webhook",
        ):
            with patch("apps.livia_assistant.crm_bridge.urlopen") as mocked_urlopen:
                LiviaCRMBridge().create_or_update_crm_lead(self.livia_lead)
        mocked_urlopen.assert_not_called()

    def test_bridge_does_not_duplicate_by_email_or_phone(self):
        first = LiviaCRMBridge().create_or_update_crm_lead(self.livia_lead)
        duplicate = LiviaLeadCapture.objects.create(
            conversation=self.conversation,
            name="Cliente Duplicado",
            email="cliente@example.com",
            phone="11999999999",
            company="Outra Empresa",
            city="São Paulo",
            service_interest="PMOC",
            is_qualified=True,
        )

        second = LiviaCRMBridge().create_or_update_crm_lead(duplicate)

        self.assertEqual(first.id, second.id)
        self.assertEqual(Lead.objects.count(), 1)

    def test_bridge_deduplicates_by_email_and_source_not_global_email(self):
        from apps.growth_engine.models import LeadSource

        other_source = LeadSource.objects.create(name="Origem Externa", source_type=LeadSource.SourceType.PARTNER)
        lead_other_source = Lead.objects.create(
            company_name="Empresa Externa",
            email="cliente@example.com",
            phone="11888887777",
            source=other_source,
            status=Lead.Status.NEW,
        )
        synced = LiviaCRMBridge().create_or_update_crm_lead(self.livia_lead)

        self.assertIsNotNone(synced)
        self.assertEqual(Lead.objects.count(), 2)
        self.assertNotEqual(synced.id, lead_other_source.id)

    def test_bridge_deduplicates_by_phone_and_source_when_email_present(self):
        first = LiviaLeadCapture.objects.create(
            conversation=self.conversation,
            name="Contato Um",
            email="contato1@example.com",
            phone="11911112222",
            company="Empresa Um",
            city="São Paulo",
            service_interest="diagnóstico técnico",
            notes="linha parada",
            is_qualified=True,
        )
        second = LiviaLeadCapture.objects.create(
            conversation=self.conversation,
            name="Contato Dois",
            email="contato1@example.com",
            phone="11911112222",
            company="Empresa Dois",
            city="São Paulo",
            service_interest="diagnóstico técnico",
            notes="suporte",
            is_qualified=True,
        )

        first_crm = LiviaCRMBridge().create_or_update_crm_lead(first)
        second_crm = LiviaCRMBridge().create_or_update_crm_lead(second)

        self.assertEqual(first_crm.id, second_crm.id)
        self.assertEqual(Lead.objects.count(), 1)

    def test_qualified_livia_lead_calls_bridge(self):
        service = LiviaAssistantService()
        conversation = LiviaConversation.objects.create(session_key="service-crm")
        extracted_data = {
            "name": "Cliente Serviço",
            "email": "servico@example.com",
            "phone": "11888887777",
            "company": "Empresa Serviço",
            "city": "São Paulo",
            "service_interest": "PMOC",
            "urgency": LiviaLeadCapture.Urgency.HIGH,
            "notes": "quero orçamento de manutenção",
        }

        with patch("apps.livia_assistant.services.LiviaCRMBridge") as bridge_class:
            bridge_class.return_value.create_or_update_crm_lead.return_value = object()
            service.create_or_update_lead_capture(conversation, extracted_data)

        bridge_class.return_value.create_or_update_crm_lead.assert_called_once()

    def test_send_to_crm_button_works(self):
        user_model = get_user_model()
        user = user_model.objects.create_superuser(
            email="crm-admin@example.com",
            password="testpass123",
            first_name="CRM",
        )
        self.client.force_login(user)

        response = self.client.post(reverse("admin-shell:livia-lead-action", args=[self.livia_lead.id, "send-to-crm"]))
        self.livia_lead.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(self.livia_lead.operational_status, LiviaLeadCapture.OperationalStatus.SENT_TO_CRM)

    def test_mark_contacted_and_create_handoff_actions(self):
        LiviaCRMBridge().create_or_update_crm_lead(self.livia_lead)
        LiviaCRMBridge().mark_contacted(self.livia_lead)
        handoff = LiviaCRMBridge().create_livia_handoff(self.livia_lead)
        self.livia_lead.refresh_from_db()

        self.assertEqual(self.livia_lead.operational_status, LiviaLeadCapture.OperationalStatus.CONTACTED)
        self.assertTrue(LeadInteraction.objects.exists())
        self.assertEqual(handoff.status, LiviaHandoffRequest.Status.PENDING)
