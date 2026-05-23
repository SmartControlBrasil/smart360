from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.growth_engine.models import CommercialProposal, Lead, LeadInteraction, LeadSource


class GrowthMarketplaceLeadDashboardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="growth-mp-admin@example.com",
            password="testpass123",
            first_name="GrowthMP",
        )
        self.client.force_login(self.user)
        self.source = LeadSource.objects.create(name="marketplace_ecom", description="Marketplace MVP")
        self.mp_lead = Lead.objects.create(
            company_name="Indústria ABC",
            contact_name="João Silva",
            email="joao@example.com",
            phone="11988887777",
            status=Lead.Status.NEW,
            source=self.source,
            metadata={
                "origin": "marketplace_ecom",
                "request_type": "quote_request",
                "product_title": "CLP Siemens S7-1200",
                "product_slug": "clp-simens",
            },
        )
        Lead.objects.create(
            company_name="Cliente Lívia Só",
            contact_name="Maria",
            email="maria@example.com",
            metadata={"source": "livia_assistant"},
        )
        Lead.objects.create(
            company_name="Somente Metadata MP",
            contact_name="Pedro",
            email="pedro@example.com",
            metadata={
                "origin": "marketplace_ecom",
                "product_title": "Servo Motor",
            },
        )

    def test_marketplace_list_contains_marketplace_leads_only(self):
        response = self.client.get(reverse("admin-shell:growth-marketplace-leads"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Indústria ABC")
        self.assertContains(response, "Somente Metadata MP")
        self.assertContains(response, "CLP Siemens S7-1200")
        self.assertNotContains(response, "Cliente Lívia Só")

    def test_filters_by_status_period_and_search(self):
        Lead.objects.filter(pk=self.mp_lead.pk).update(status=Lead.Status.CONTACTED)
        since = timezone.localdate()

        qs = {"status": "contacted", "date_from": since.isoformat(), "date_to": since.isoformat(), "q": "Indústria"}
        response = self.client.get(reverse("admin-shell:growth-marketplace-leads"), qs)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Indústria ABC")
        self.assertNotContains(response, "Somente Metadata MP")

    def test_period_excludes_old_lead(self):
        old = timezone.now() - timedelta(days=40)
        lead = Lead.objects.create(
            company_name="Lead Velho MP",
            email="velho@example.com",
            source=self.source,
            metadata={"origin": "marketplace_ecom"},
        )
        Lead.objects.filter(pk=lead.pk).update(created_at=old)

        since = timezone.localdate().isoformat()
        response = self.client.get(reverse("admin-shell:growth-marketplace-leads"), {"date_from": since})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Indústria ABC")
        self.assertNotContains(response, "Lead Velho MP")

    def _marketplace_detail_url(self, pk):
        return reverse("admin-shell:growth-marketplace-lead-detail", kwargs={"lead_id": pk})

    def test_marketplace_detail_resolves_for_marketplace_lead(self):
        url = self._marketplace_detail_url(self.mp_lead.pk)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Indústria ABC")
        self.assertContains(response, "Nova interação comercial")
        self.assertContains(response, "Alterar status do lead")
        self.assertContains(response, "CLP Siemens S7-1200")
        self.assertContains(response, "Proposta comercial")
        self.assertContains(response, "Criar proposta")

    def test_marketplace_detail_returns_404_for_non_marketplace_lead(self):
        livia_pk = Lead.objects.get(company_name="Cliente Lívia Só").pk
        response = self.client.get(self._marketplace_detail_url(livia_pk))
        self.assertEqual(response.status_code, 404)

    def test_marketplace_add_interaction_creates_record_and_redirects(self):
        url = self._marketplace_detail_url(self.mp_lead.pk)
        response = self.client.post(
            url,
            {
                "interaction_submit": "1",
                "interaction_type": LeadInteraction.InteractionType.NOTE,
                "channel": LeadInteraction.Channel.OTHER,
                "summary": "Cliente pediu retorno na segunda-feira.",
            },
        )
        self.assertRedirects(response, url, fetch_redirect_response=False)
        ix = LeadInteraction.objects.get(lead=self.mp_lead)
        self.assertEqual(ix.summary, "Cliente pediu retorno na segunda-feira.")
        self.assertEqual(ix.owner_id, self.user.pk)

    def test_marketplace_update_status_persists(self):
        url = self._marketplace_detail_url(self.mp_lead.pk)
        response = self.client.post(url, {"status_submit": "1", "status": Lead.Status.CONTACTED})
        self.assertRedirects(response, url, fetch_redirect_response=False)
        self.mp_lead.refresh_from_db()
        self.assertEqual(self.mp_lead.status, Lead.Status.CONTACTED)

    def _create_proposal_url(self, pk):
        return reverse("admin-shell:growth-marketplace-lead-create-proposal", kwargs={"lead_id": pk})

    def test_marketplace_detail_shows_view_proposal_when_linked(self):
        proposal = CommercialProposal.objects.create(
            proposal_number="GPRO-CTX-7777",
            lead=self.mp_lead,
            company_name=self.mp_lead.company_name,
            status=CommercialProposal.Status.DRAFT,
        )
        response = self.client.get(self._marketplace_detail_url(self.mp_lead.pk))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ver proposta")
        self.assertContains(response, proposal.proposal_number)

    def test_marketplace_post_create_proposal_redirects_and_enriches(self):
        ix_before = LeadInteraction.objects.filter(lead=self.mp_lead).count()
        rsp = self.client.post(self._create_proposal_url(self.mp_lead.pk))
        proposal = CommercialProposal.objects.get(lead=self.mp_lead)
        detail_url = reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": proposal.pk})
        self.assertRedirects(rsp, detail_url, fetch_redirect_response=False)
        self.assertEqual(proposal.origin, "marketplace_ecom")
        self.assertEqual(proposal.metadata.get("marketplace_lead_id"), self.mp_lead.pk)
        self.assertIn("Marketplace", proposal.summary or "")
        self.assertIn("CLP Siemens", proposal.summary or "")
        self.mp_lead.refresh_from_db()
        self.assertEqual(self.mp_lead.status, Lead.Status.PROPOSAL)
        self.assertEqual(self.mp_lead.metadata.get("proposal_id"), proposal.id)
        self.assertGreater(LeadInteraction.objects.filter(lead=self.mp_lead).count(), ix_before)
        last_ix = LeadInteraction.objects.filter(lead=self.mp_lead).order_by("-id").first()
        self.assertIn(proposal.proposal_number, last_ix.summary)

    def test_marketplace_post_create_proposal_returns_404_for_non_marketplace_lead(self):
        livia_pk = Lead.objects.get(company_name="Cliente Lívia Só").pk
        rsp = self.client.post(self._create_proposal_url(livia_pk))
        self.assertEqual(rsp.status_code, 404)

    def test_marketplace_post_create_proposal_idempotent_when_proposal_linked(self):
        existing = CommercialProposal.objects.create(
            proposal_number="GPRO-DUPCHK-9911",
            lead=self.mp_lead,
            company_name=self.mp_lead.company_name,
            status=CommercialProposal.Status.DRAFT,
        )
        ix_before = LeadInteraction.objects.filter(lead=self.mp_lead).count()
        rsp = self.client.post(self._create_proposal_url(self.mp_lead.pk))
        self.assertRedirects(
            rsp,
            reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": existing.pk}),
            fetch_redirect_response=False,
        )
        self.assertEqual(CommercialProposal.objects.filter(lead=self.mp_lead).count(), 1)
        self.assertEqual(LeadInteraction.objects.filter(lead=self.mp_lead).count(), ix_before)

    def test_marketplace_existing_proposal_found_by_metadata_without_fk(self):
        orphan = CommercialProposal.objects.create(
            proposal_number="GPRO-METAMARK-7711",
            lead=None,
            company_name=self.mp_lead.company_name,
            status=CommercialProposal.Status.DRAFT,
            metadata={"marketplace_lead_id": self.mp_lead.pk},
        )
        ix_before = LeadInteraction.objects.filter(lead=self.mp_lead).count()
        rsp = self.client.post(self._create_proposal_url(self.mp_lead.pk))
        self.assertRedirects(
            rsp,
            reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": orphan.pk}),
            fetch_redirect_response=False,
        )
        self.assertEqual(CommercialProposal.objects.filter(pk=orphan.pk).count(), 1)
        self.assertEqual(LeadInteraction.objects.filter(lead=self.mp_lead).count(), ix_before)

    def test_marketplace_proposal_detail_shows_origem_and_back_link(self):
        rsp = self.client.post(self._create_proposal_url(self.mp_lead.pk))
        self.assertEqual(rsp.status_code, 302)
        proposal = CommercialProposal.objects.get(lead=self.mp_lead)
        detail = self.client.get(reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": proposal.pk}))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Origem técnica Marketplace")
        self.assertContains(detail, "Origem da demanda")
        self.assertContains(detail, "Produto ou solução solicitada")
        self.assertContains(detail, "Observações técnicas")
        self.assertContains(detail, "Marketplace técnico")
        self.assertContains(detail, f"/dashboard/growth/marketplace-leads/{self.mp_lead.pk}/")

    def test_plain_proposal_detail_hides_marketplace_block(self):
        proposal = CommercialProposal.objects.create(
            proposal_number="GPRO-PLAIN-8877",
            company_name="Cliente Genérico",
            origin="growth_engine",
            metadata={"proposal_origin": "growth_engine"},
            status=CommercialProposal.Status.DRAFT,
        )
        rsp = self.client.get(reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": proposal.pk}))
        self.assertEqual(rsp.status_code, 200)
        self.assertNotContains(rsp, "Origem técnica Marketplace")
        self.assertNotContains(rsp, "Trecho sugerido — corpo de e-mail")

    def test_proposal_helper_detects_origin_from_metadata(self):
        from apps.growth_engine.proposal_helpers import commercial_proposal_is_marketplace_origin

        placeholder = CommercialProposal(
            proposal_number="GPRO-HLP-PLACE",
            company_name="Empresa Teste Aux",
            origin="internal",
            metadata={"proposal_origin": "marketplace_ecom"},
            status=CommercialProposal.Status.DRAFT,
            total_value=0,
        )
        self.assertTrue(commercial_proposal_is_marketplace_origin(placeholder))
