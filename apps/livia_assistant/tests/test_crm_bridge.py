from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.growth_engine.models import Lead, LeadInteraction
from apps.livia_assistant.crm_bridge import LiviaCRMBridge
from apps.livia_assistant.models import LiviaConversation, LiviaHandoffRequest, LiviaLeadCapture
from apps.livia_assistant.services import LiviaAssistantService


class LiviaCRMBridgeTests(TestCase):
    def setUp(self):
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

    def test_bridge_does_not_duplicate_by_email_or_phone(self):
        first = LiviaCRMBridge().create_or_update_crm_lead(self.livia_lead)
        duplicate = LiviaLeadCapture.objects.create(
            conversation=self.conversation,
            name="Cliente Duplicado",
            email="cliente@example.com",
            phone="11999999999",
            company="Outra Empresa",
            service_interest="PMOC",
            is_qualified=True,
        )

        second = LiviaCRMBridge().create_or_update_crm_lead(duplicate)

        self.assertEqual(first.id, second.id)
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
            "notes": "quero orçamento",
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
