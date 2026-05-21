from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.growth_engine.models import CommercialProposal, Lead, LeadInteraction
from apps.livia_assistant.models import LiviaConversation, LiviaHandoffRequest, LiviaLeadCapture


class GrowthLiviaLeadDashboardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="growth-livia-admin@example.com",
            password="testpass123",
            first_name="Growth",
        )
        self.client.force_login(self.user)
        self.conversation = LiviaConversation.objects.create(session_key="growth-livia-session")
        LiviaHandoffRequest.objects.create(
            conversation=self.conversation,
            reason="Lead pede atendimento humano.",
        )
        self.livia_capture = LiviaLeadCapture.objects.create(
            conversation=self.conversation,
            name="Cliente Lívia",
            email="livia@example.com",
            phone="11999999999",
            company="Empresa Lívia",
            service_interest="PMOC",
            urgency=LiviaLeadCapture.Urgency.HIGH,
            notes="Resumo capturado pela Lívia",
            is_qualified=True,
            operational_status=LiviaLeadCapture.OperationalStatus.SENT_TO_CRM,
        )
        self.livia_lead = Lead.objects.create(
            company_name="Empresa Lívia",
            contact_name="Cliente Lívia",
            email="livia@example.com",
            phone="11999999999",
            whatsapp="11999999999",
            city="São Paulo",
            status=Lead.Status.QUALIFIED,
            notes="Resumo capturado pela Lívia",
            metadata={
                "source": "livia_assistant",
                "service_interest": "PMOC",
                "urgency": "high",
                "livia_conversation_id": self.conversation.id,
                "livia_lead_id": self.livia_capture.id,
            },
        )
        self.livia_capture.crm_lead_id = self.livia_lead.id
        self.livia_capture.save(update_fields=["crm_lead_id"])
        Lead.objects.create(
            company_name="Empresa Externa",
            contact_name="Cliente Externo",
            email="externo@example.com",
            metadata={"source": "manual"},
        )

    def test_livia_lead_view_shows_only_livia_leads(self):
        response = self.client.get(reverse("admin-shell:growth-livia-leads"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Empresa Lívia")
        self.assertContains(response, "PMOC")
        self.assertContains(response, "Handoffs pendentes")
        self.assertNotContains(response, "Empresa Externa")

    def test_growth_lead_detail_responds_for_admin_user(self):
        response = self.client.get(reverse("admin-shell:growth-lead-detail", args=[self.livia_lead.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Empresa Lívia")
        self.assertContains(response, "Origem Lívia")
        self.assertContains(response, "Abrir conversa da Lívia")
        self.assertContains(response, "Resumo capturado pela Lívia")
        self.assertContains(response, "Sent to CRM")
        self.assertContains(response, "Criar proposta")

    def _post_action(self, action):
        return self.client.post(reverse("admin-shell:growth-lead-action", args=[self.livia_lead.id, action]))

    def _assert_action_metadata(self, action):
        self.livia_lead.refresh_from_db()
        self.assertEqual(self.livia_lead.metadata["last_action"], action)
        self.assertIn("last_action_at", self.livia_lead.metadata)
        self.assertEqual(self.livia_lead.metadata["last_action_by"], self.user.email)
        self.assertTrue(self.livia_lead.metadata["livia_origin"])
        self.assertTrue(LeadInteraction.objects.filter(lead=self.livia_lead).exists())

    def test_mark_contacted_updates_status_metadata_and_interaction(self):
        response = self._post_action("mark-contacted")

        self.assertEqual(response.status_code, 302)
        self.livia_lead.refresh_from_db()
        self.assertEqual(self.livia_lead.status, Lead.Status.CONTACTED)
        self._assert_action_metadata("mark-contacted")

    def test_mark_lost_updates_status_metadata_and_interaction(self):
        response = self._post_action("mark-lost")

        self.assertEqual(response.status_code, 302)
        self.livia_lead.refresh_from_db()
        self.assertEqual(self.livia_lead.status, Lead.Status.LOST)
        self._assert_action_metadata("mark-lost")

    def test_mark_converted_updates_status_metadata_and_interaction(self):
        response = self._post_action("mark-converted")

        self.assertEqual(response.status_code, 302)
        self.livia_lead.refresh_from_db()
        self.assertEqual(self.livia_lead.status, Lead.Status.WON)
        self._assert_action_metadata("mark-converted")

    def test_move_to_proposal_updates_status_metadata_and_redirects(self):
        response = self._post_action("move-to-proposal")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("admin-shell:growth-lead-create-proposal", args=[self.livia_lead.id]))
        self.livia_lead.refresh_from_db()
        self.assertEqual(self.livia_lead.status, Lead.Status.PROPOSAL)
        self.assertTrue(self.livia_lead.metadata["proposal_requires_human_confirmation"])
        self.assertEqual(self.livia_lead.metadata["proposal_prefill"]["company_name"], "Empresa Lívia")
        self.assertFalse(CommercialProposal.objects.filter(lead=self.livia_lead).exists())
        self._assert_action_metadata("move-to-proposal")

    def test_create_proposal_form_prefills_lead_data(self):
        response = self.client.get(reverse("admin-shell:growth-lead-create-proposal", args=[self.livia_lead.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Empresa Lívia")
        self.assertContains(response, "Cliente Lívia")
        self.assertContains(response, "PMOC")
        self.assertContains(response, "Resumo capturado pela Lívia")

    def test_save_proposal_updates_lead_and_creates_interaction(self):
        response = self.client.post(
            reverse("admin-shell:growth-lead-create-proposal", args=[self.livia_lead.id]),
            {
                "company_name": "Empresa Lívia",
                "contact_name": "Cliente Lívia",
                "email": "livia@example.com",
                "phone": "11999999999",
                "service_interest": "PMOC",
                "urgency": "high",
                "origin": "livia_assistant",
                "summary": "Resumo capturado pela Lívia",
                "scope": "PMOC",
                "customer_message": "Proposta em rascunho para revisão humana.",
                "total_value": "1500.00",
            },
        )

        proposal = CommercialProposal.objects.get(lead=self.livia_lead)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("admin-shell:growth-proposal-detail", args=[proposal.id]))
        self.assertEqual(proposal.company_name, "Empresa Lívia")
        self.assertEqual(proposal.metadata["proposal_origin"], "livia_assistant")
        self.assertTrue(proposal.metadata["livia_origin"])

        self.livia_lead.refresh_from_db()
        self.assertEqual(self.livia_lead.status, Lead.Status.PROPOSAL)
        self.assertEqual(self.livia_lead.metadata["proposal_id"], proposal.id)
        self.assertEqual(self.livia_lead.metadata["proposal_origin"], "livia_assistant")
        self.assertIn("proposal_created_at", self.livia_lead.metadata)
        self.assertTrue(
            LeadInteraction.objects.filter(
                lead=self.livia_lead,
                summary__contains=proposal.proposal_number,
            ).exists()
        )

    def test_existing_proposal_redirects_without_duplicate(self):
        proposal = CommercialProposal.objects.create(
            proposal_number="GPRO-2026-9999",
            lead=self.livia_lead,
            company_name="Empresa Lívia",
            contact_name="Cliente Lívia",
            email="livia@example.com",
            phone="11999999999",
            service_interest="PMOC",
            urgency="high",
            origin="livia_assistant",
            total_value="1500.00",
        )

        get_response = self.client.get(reverse("admin-shell:growth-lead-create-proposal", args=[self.livia_lead.id]))
        post_response = self.client.post(
            reverse("admin-shell:growth-lead-create-proposal", args=[self.livia_lead.id]),
            {
                "company_name": "Empresa Lívia",
                "total_value": "2000.00",
            },
        )

        self.assertEqual(get_response.status_code, 302)
        self.assertEqual(get_response["Location"], reverse("admin-shell:growth-proposal-detail", args=[proposal.id]))
        self.assertEqual(post_response.status_code, 302)
        self.assertEqual(CommercialProposal.objects.filter(lead=self.livia_lead).count(), 1)

    def test_growth_lead_detail_shows_existing_proposal_link(self):
        proposal = CommercialProposal.objects.create(
            proposal_number="GPRO-2026-9998",
            lead=self.livia_lead,
            company_name="Empresa Lívia",
        )

        response = self.client.get(reverse("admin-shell:growth-lead-detail", args=[self.livia_lead.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ver proposta")
        self.assertContains(response, proposal.proposal_number)


class GrowthLeadAPILiviaFilterTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="growth-api@example.com",
            password="testpass123",
            first_name="API",
        )
        self.client.force_authenticate(self.user)
        Lead.objects.create(
            company_name="Lead API Lívia",
            email="api-livia@example.com",
            metadata={"source": "livia_assistant", "service_interest": "Automação"},
        )
        Lead.objects.create(
            company_name="Lead API Manual",
            email="api-manual@example.com",
            metadata={"source": "manual"},
        )

    def test_api_source_origin_filter_returns_only_livia_leads(self):
        response = self.client.get(reverse("growth-leads-list"), {"source_origin": "livia"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        serialized = payload.get("results", payload) if isinstance(payload, dict) else payload
        names = {item["company_name"] for item in serialized}
        self.assertIn("Lead API Lívia", names)
        self.assertNotIn("Lead API Manual", names)
