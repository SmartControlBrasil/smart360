from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.growth_engine.models import CommercialProposal, Lead, LeadSource


class GrowthApprovedProposalsListViewTests(TestCase):
    """Lista operacional só com propostas em status accepted."""

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="growth-approved-list@example.com",
            password="testpass123",
            first_name="ApprovedList",
        )
        self.client.force_login(self.user)
        self.lead = Lead.objects.create(
            company_name="Cliente Com Lead",
            contact_name="Fulano Silva",
            email="fulano@accepted.example.com",
            phone="11999991111",
        )
        self.accepted_visible = CommercialProposal.objects.create(
            proposal_number="GPRO-LIST-ACC-visible",
            lead=self.lead,
            company_name="Cliente Com Lead",
            contact_name="Fulano Silva",
            email="fulano@accepted.example.com",
            phone="11999991111",
            status=CommercialProposal.Status.ACCEPTED,
            origin="site",
            service_interest="Automação",
            total_value=Decimal("4200.00"),
        )

    def test_list_contains_only_accepted_proposals(self):
        CommercialProposal.objects.create(
            proposal_number="GPRO-LIST-draft-hide",
            lead=None,
            company_name="Somente Draft",
            status=CommercialProposal.Status.DRAFT,
        )
        CommercialProposal.objects.create(
            proposal_number="GPRO-LIST-sent-hide",
            lead=None,
            company_name="Somente Sent",
            status=CommercialProposal.Status.SENT,
        )
        CommercialProposal.objects.create(
            proposal_number="GPRO-LIST-rejected-hide",
            lead=None,
            company_name="Somente Rejected",
            status=CommercialProposal.Status.REJECTED,
        )
        CommercialProposal.objects.create(
            proposal_number="GPRO-LIST-expired-hide",
            lead=None,
            company_name="Somente Expired",
            status=CommercialProposal.Status.EXPIRED,
        )

        rsp = self.client.get(reverse("admin-shell:growth-proposals-approved"))

        self.assertEqual(rsp.status_code, 200)
        self.assertContains(rsp, self.accepted_visible.proposal_number)
        self.assertNotContains(rsp, "GPRO-LIST-draft-hide")
        self.assertNotContains(rsp, "Somente Draft")
        self.assertNotContains(rsp, "GPRO-LIST-sent-hide")
        self.assertNotContains(rsp, "GPRO-LIST-rejected-hide")
        self.assertNotContains(rsp, "GPRO-LIST-expired-hide")

    def test_accepted_marketplace_row_shows_marketplace_indicator(self):
        source, _ = LeadSource.objects.get_or_create(name="marketplace_ecom", defaults={"description": "test"})
        mp_lead = Lead.objects.create(
            company_name="Cliente MP Lista",
            source=source,
            metadata={"origin": "marketplace_ecom"},
        )
        mp_accepted = CommercialProposal.objects.create(
            proposal_number="GPRO-LIST-MP-acc",
            lead=mp_lead,
            company_name=mp_lead.company_name,
            status=CommercialProposal.Status.ACCEPTED,
            origin="marketplace_ecom",
            service_interest="CLP XYZ",
            metadata={"marketplace_lead_id": mp_lead.pk, "proposal_origin": "marketplace_ecom"},
        )

        rsp = self.client.get(reverse("admin-shell:growth-proposals-approved"))

        self.assertEqual(rsp.status_code, 200)
        self.assertContains(rsp, mp_accepted.proposal_number)
        self.assertContains(rsp, "Marketplace E-com")
        self.assertContains(rsp, "Lead Marketplace")
        self.assertContains(
            rsp,
            reverse("admin-shell:growth-marketplace-lead-detail", kwargs={"lead_id": mp_lead.pk}),
        )


class GrowthProposalOperationalDetailBlockTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="growth-op-block@example.com",
            password="testpass123",
            first_name="OpBlock",
        )
        self.client.force_login(self.user)
        self.lead = Lead.objects.create(company_name="Co Block", email="block@example.com")
        self.proposal = CommercialProposal.objects.create(
            proposal_number="GPRO-OP-BLK-001",
            lead=self.lead,
            company_name="Co Block",
            status=CommercialProposal.Status.DRAFT,
        )

    def test_accepted_detail_shows_operational_next_step_message(self):
        CommercialProposal.objects.filter(pk=self.proposal.pk).update(status=CommercialProposal.Status.ACCEPTED)
        rsp = self.client.get(
            reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": self.proposal.pk}),
        )
        self.assertEqual(rsp.status_code, 200)
        self.assertContains(rsp, "Próxima etapa operacional")
        self.assertContains(rsp, "encaminhamento operacional")
        self.assertContains(rsp, "Fila: propostas aprovadas")

    def test_non_accepted_detail_hides_operational_block(self):
        rsp = self.client.get(
            reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": self.proposal.pk}),
        )
        self.assertEqual(rsp.status_code, 200)
        self.assertNotContains(rsp, "Próxima etapa operacional")
        self.assertNotContains(rsp, "Fila: propostas aprovadas")


class GrowthMarketplaceAcceptedOperationalIntegrationTests(TestCase):
    """Proposta marketplace aceita: painel técnico + bloco operacional."""

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="growth-mp-acc-op@example.com",
            password="testpass123",
            first_name="MPAcc",
        )
        self.client.force_login(self.user)
        source, _ = LeadSource.objects.get_or_create(name="marketplace_ecom", defaults={"description": "test"})
        self.mp_lead = Lead.objects.create(
            company_name="Empresa MP Aprovada",
            contact_name="Contato MP",
            email="mp-acc@example.com",
            source=source,
            metadata={"origin": "marketplace_ecom", "product_title": "Item catálogo"},
        )
        self.proposal = CommercialProposal.objects.create(
            proposal_number="GPRO-MP-ACC-OPS-001",
            lead=self.mp_lead,
            company_name=self.mp_lead.company_name,
            origin="marketplace_ecom",
            status=CommercialProposal.Status.ACCEPTED,
            metadata={"marketplace_lead_id": self.mp_lead.pk},
        )

    def test_accepted_mp_detail_keeps_technical_panel_and_shows_operational_block(self):
        rsp = self.client.get(
            reverse("admin-shell:growth-proposal-detail", kwargs={"proposal_id": self.proposal.pk}),
        )
        self.assertEqual(rsp.status_code, 200)
        self.assertContains(rsp, "Origem técnica Marketplace")
        self.assertContains(rsp, "Próxima etapa operacional")
