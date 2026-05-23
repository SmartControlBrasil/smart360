from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.growth_engine.models import CommercialProposal, Lead, LeadInteraction, LeadSource


class GrowthCommercialProposalOperationalForwardViewTests(TestCase):
    """Encaminhamento operacional POST + metadata + LeadInteraction."""

    NOTE_TEXT = "Iniciar com equipe TPM após revisão técnica de campo."

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="growth-op-fw@example.com",
            password="testpass123",
            first_name="OpForward",
            last_name="User",
        )
        self.client.force_login(self.user)
        self.lead = Lead.objects.create(company_name="Co FW", email="fw@example.com")
        self.proposal = CommercialProposal.objects.create(
            proposal_number="GPRO-FW-0001",
            lead=self.lead,
            company_name="Co FW",
            status=CommercialProposal.Status.ACCEPTED,
        )

    def _forward_url(self, pk=None):
        return reverse(
            "admin-shell:growth-proposal-operational-forward",
            kwargs={"proposal_id": pk or self.proposal.pk},
        )

    def test_accepted_detail_shows_forward_form(self):
        rsp = self.client.get(
            reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": self.proposal.pk}),
        )
        self.assertEqual(rsp.status_code, 200)
        self.assertContains(rsp, "Registrar encaminhamento operacional")
        self.assertContains(rsp, 'name="note"')

    def test_post_accepted_persists_metadata_and_creates_lead_interaction(self):
        before = LeadInteraction.objects.filter(lead=self.lead).count()
        rsp = self.client.post(self._forward_url(), {"note": self.NOTE_TEXT})
        self.assertRedirects(
            rsp,
            reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": self.proposal.pk}),
            fetch_redirect_response=False,
        )
        self.proposal.refresh_from_db()
        md = self.proposal.metadata or {}
        self.assertIn("operational_forwarded_at", md)
        self.assertEqual(md.get("operational_forward_note"), self.NOTE_TEXT)
        self.assertEqual(md.get("operational_forwarded_by_id"), self.user.pk)
        self.assertEqual(LeadInteraction.objects.filter(lead=self.lead).count(), before + 1)
        last_ix = LeadInteraction.objects.filter(lead=self.lead).order_by("-id").first()
        self.assertIn("Proposta encaminhada para etapa operacional", last_ix.summary)
        self.assertIn(self.proposal.proposal_number, last_ix.summary)
        self.assertIn(self.NOTE_TEXT, last_ix.summary)

    def test_post_non_accepted_rejected_without_metadata_changes(self):
        CommercialProposal.objects.filter(pk=self.proposal.pk).update(status=CommercialProposal.Status.DRAFT)
        self.proposal.refresh_from_db()
        md_before = dict(self.proposal.metadata or {})
        self.client.post(self._forward_url(), {"note": self.NOTE_TEXT})
        self.proposal.refresh_from_db()
        self.assertFalse((self.proposal.metadata or {}).get("operational_forwarded_at"))
        self.assertEqual(self.proposal.metadata or {}, md_before)

    def test_forwarded_detail_hides_form_shows_summary(self):
        self.client.post(self._forward_url(), {"note": self.NOTE_TEXT})
        rsp = self.client.get(
            reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": self.proposal.pk}),
        )
        self.assertEqual(rsp.status_code, 200)
        self.assertNotContains(rsp, "Registrar encaminhamento operacional")
        self.assertContains(rsp, "Já registrada como encaminhada")
        self.assertContains(rsp, self.NOTE_TEXT)
        self.assertContains(rsp, "OpForward User")

    def test_second_forward_post_blocked(self):
        self.client.post(self._forward_url(), {"note": self.NOTE_TEXT})
        alt = "Tentativa de sobrescrever que não deve vencer."
        self.client.post(self._forward_url(), {"note": alt})
        self.proposal.refresh_from_db()
        self.assertEqual((self.proposal.metadata or {}).get("operational_forward_note"), self.NOTE_TEXT)

    def test_accepted_without_lead_saves_metadata_no_interaction(self):
        orphan = CommercialProposal.objects.create(
            proposal_number="GPRO-FW-ORPH",
            lead=None,
            company_name="SEM LEAD FW",
            status=CommercialProposal.Status.ACCEPTED,
        )
        before_ix = LeadInteraction.objects.count()
        self.client.post(
            reverse(
                "admin-shell:growth-proposal-operational-forward",
                kwargs={"proposal_id": orphan.pk},
            ),
            {"note": "Cliente direto sem CRM lead."},
        )
        orphan.refresh_from_db()
        self.assertTrue((orphan.metadata or {}).get("operational_forwarded_at"))
        self.assertEqual(LeadInteraction.objects.count(), before_ix)


class GrowthMarketplaceOperationalForwardPanelTests(TestCase):
    """Bloco técnico marketplace + formulário encaminhamento em aceita."""

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="growth-mp-fw@example.com",
            password="testpass123",
            first_name="MPFW",
        )
        self.client.force_login(self.user)
        source, _ = LeadSource.objects.get_or_create(name="marketplace_ecom", defaults={"description": "t"})
        self.mp_lead = Lead.objects.create(
            company_name="MP FW Co",
            source=source,
            metadata={"origin": "marketplace_ecom"},
        )
        self.proposal = CommercialProposal.objects.create(
            proposal_number="GPRO-MP-FW-001",
            lead=self.mp_lead,
            company_name=self.mp_lead.company_name,
            origin="marketplace_ecom",
            status=CommercialProposal.Status.ACCEPTED,
            metadata={"marketplace_lead_id": self.mp_lead.pk},
        )

    def test_marketplace_accepted_detail_keeps_technical_panel_and_forward_form(self):
        rsp = self.client.get(
            reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": self.proposal.pk}),
        )
        self.assertEqual(rsp.status_code, 200)
        self.assertContains(rsp, "Origem técnica Marketplace")
        self.assertContains(rsp, "Próxima etapa operacional")
        self.assertContains(rsp, "Registrar encaminhamento operacional")
