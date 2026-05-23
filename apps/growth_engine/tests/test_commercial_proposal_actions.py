from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.growth_engine.models import CommercialProposal, Lead, LeadInteraction, LeadSource


class GrowthCommercialProposalActionViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="growth-prop-actions@example.com",
            password="testpass123",
            first_name="Actions",
        )
        self.client.force_login(self.user)
        self.lead = Lead.objects.create(
            company_name="ACME Indústria",
            contact_name="Contato",
            email="contato@acme.example.com",
            status=Lead.Status.PROPOSAL,
        )
        self.proposal = CommercialProposal.objects.create(
            proposal_number="GPRO-ACT-0001",
            lead=self.lead,
            company_name="ACME Indústria",
            status=CommercialProposal.Status.DRAFT,
        )

    def test_mark_sent_updates_status_and_creates_lead_interaction(self):
        url = reverse("admin-shell:growth-proposal-mark-sent", kwargs={"proposal_id": self.proposal.pk})
        before_ix = LeadInteraction.objects.filter(lead=self.lead).count()
        rsp = self.client.post(url)
        self.assertRedirects(
            rsp,
            reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": self.proposal.pk}),
            fetch_redirect_response=False,
        )
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, CommercialProposal.Status.SENT)
        self.assertEqual(LeadInteraction.objects.filter(lead=self.lead).count(), before_ix + 1)
        last_ix = LeadInteraction.objects.filter(lead=self.lead).order_by("-id").first()
        self.assertIn("mark-sent", last_ix.summary)
        self.assertIn(self.proposal.proposal_number, last_ix.summary)

    def test_approve_from_sent_moves_to_accepted(self):
        CommercialProposal.objects.filter(pk=self.proposal.pk).update(status=CommercialProposal.Status.SENT)
        url = reverse("admin-shell:growth-proposal-approve", kwargs={"proposal_id": self.proposal.pk})
        rsp = self.client.post(url)
        self.assertRedirects(
            rsp,
            reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": self.proposal.pk}),
            fetch_redirect_response=False,
        )
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, CommercialProposal.Status.ACCEPTED)

    def test_reject_from_draft(self):
        url = reverse("admin-shell:growth-proposal-reject", kwargs={"proposal_id": self.proposal.pk})
        rsp = self.client.post(url)
        self.assertRedirects(
            rsp,
            reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": self.proposal.pk}),
            fetch_redirect_response=False,
        )
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, CommercialProposal.Status.REJECTED)

    def test_proposal_without_lead_does_not_create_interaction(self):
        orphan = CommercialProposal.objects.create(
            proposal_number="GPRO-ACT-0999",
            lead=None,
            company_name="SEM LEAD LTDA",
            status=CommercialProposal.Status.DRAFT,
        )
        before = LeadInteraction.objects.count()
        self.client.post(
            reverse("admin-shell:growth-proposal-mark-sent", kwargs={"proposal_id": orphan.pk}),
        )
        self.assertEqual(LeadInteraction.objects.count(), before)

    def test_invalid_mark_sent_when_already_sent_leaves_status(self):
        CommercialProposal.objects.filter(pk=self.proposal.pk).update(status=CommercialProposal.Status.SENT)
        self.client.post(
            reverse("admin-shell:growth-proposal-mark-sent", kwargs={"proposal_id": self.proposal.pk}),
        )
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, CommercialProposal.Status.SENT)

    def test_terminal_status_hides_quick_actions_on_detail_html(self):
        CommercialProposal.objects.filter(pk=self.proposal.pk).update(status=CommercialProposal.Status.ACCEPTED)
        rsp = self.client.get(
            reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": self.proposal.pk}),
        )
        self.assertEqual(rsp.status_code, 200)
        self.assertNotContains(rsp, "Marcar como enviada")
        self.assertNotContains(rsp, "Aprovar proposta")


class GrowthMarketplaceProposalActionsIntegrationTests(TestCase):
    """Confirma que o painel marketplace permanece junto das ações comerciais."""

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="growth-mp-prop-act@example.com",
            password="testpass123",
            first_name="MPAct",
        )
        self.client.force_login(self.user)
        self.source = LeadSource.objects.create(name="marketplace_ecom")
        self.mp_lead = Lead.objects.create(
            company_name="Indústria MP",
            contact_name="Fulano",
            email="mp@example.com",
            phone="11888887777",
            source=self.source,
            metadata={
                "origin": "marketplace_ecom",
                "product_title": "Item catalogado X",
                "product_slug": "item-x",
            },
            status=Lead.Status.PROPOSAL,
        )
        self.proposal = CommercialProposal.objects.create(
            proposal_number="GPRO-MP-ACT-0001",
            lead=self.mp_lead,
            company_name=self.mp_lead.company_name,
            origin="marketplace_ecom",
            status=CommercialProposal.Status.DRAFT,
            metadata={
                "marketplace_lead_id": self.mp_lead.pk,
                "proposal_origin": "marketplace_ecom",
                "product_title": "Item catalogado X",
            },
        )

    def test_marketplace_panel_and_actions_visible_in_draft(self):
        rsp = self.client.get(
            reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": self.proposal.pk}),
        )
        self.assertEqual(rsp.status_code, 200)
        self.assertContains(rsp, "Origem técnica Marketplace")
        self.assertContains(rsp, "Marcar como enviada")

    def test_marketplace_panel_remains_after_mark_sent(self):
        self.client.post(
            reverse("admin-shell:growth-proposal-mark-sent", kwargs={"proposal_id": self.proposal.pk}),
        )
        rsp = self.client.get(
            reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": self.proposal.pk}),
        )
        self.assertContains(rsp, "Origem técnica Marketplace")
        self.assertNotContains(rsp, "Marcar como enviada")
        self.assertContains(rsp, "Aprovar proposta")
