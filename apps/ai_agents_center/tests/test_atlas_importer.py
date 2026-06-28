from unittest.mock import patch

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.access_control_center.services.smart_system_access import bootstrap_smart_system_access
from apps.ai_agents_center.models import CommercialOpportunity, AtlasProspectImportBatch
from apps.ai_agents_center.services.atlas_importer import AtlasImporterService
from apps.ai_agents_center.services.opportunity_builder import OpportunityBuilderService
from apps.companies.models import Membership
from apps.growth_engine.models import Lead
from tests.factories.core import CompanyFactory, MembershipFactory, UserFactory


class AtlasImporterServiceTests(TestCase):
    def setUp(self):
        bootstrap_smart_system_access()
        self.user = UserFactory(email="atlas-importer@smart360.local", password="StrongPass123")
        self.company = CompanyFactory(name="Atlas Import Company", slug="atlas-import-company")
        MembershipFactory(user=self.user, company=self.company, is_primary=True)

    def _valid_rows(self):
        return [
            {
                "company_name": "Hospital Norte",
                "segment": "Hospital",
                "city": "sao paulo",
                "state": "sp",
                "website": "https://hospital-norte.example.com",
                "contact_email": "contato@hospital-norte.example.com",
                "contact_phone": "+55 11 99999-0000",
                "contact_name": "Maria Silva",
                "notes": "Alto fluxo de limpeza em areas comuns",
                "source": "manual",
            },
            {
                "company_name": "Hotel Litoral",
                "segment": "Hotel",
                "city": "santos",
                "state": "SP",
                "contact_email": "recepcao@hotel-litoral.example.com",
                "notes": "Recepcao com alto volume de visitantes",
            },
        ]

    def test_imports_valid_list_and_creates_opportunities(self):
        batch = AtlasImporterService.import_rows(
            rows=self._valid_rows(),
            company=self.company,
            source="manual",
            created_by=self.user,
        )

        self.assertEqual(batch.status, AtlasProspectImportBatch.Status.COMPLETED)
        self.assertEqual(batch.total_rows, 2)
        self.assertEqual(batch.processed_rows, 2)
        self.assertEqual(batch.created_opportunities, 2)
        self.assertEqual(batch.skipped_duplicates, 0)
        self.assertEqual(CommercialOpportunity.objects.filter(company=self.company).count(), 2)

    def test_ignores_rows_without_company_name(self):
        rows = self._valid_rows() + [{"segment": "Sem empresa", "city": "Campinas"}]

        batch = AtlasImporterService.import_rows(rows=rows, company=self.company, source="manual")

        self.assertEqual(batch.total_rows, 3)
        self.assertEqual(batch.processed_rows, 2)
        self.assertEqual(batch.skipped_empty_rows, 1)
        self.assertEqual(batch.created_opportunities, 2)

    def test_prevents_duplicates(self):
        rows = self._valid_rows()[:1]

        first_batch = AtlasImporterService.import_rows(rows=rows, company=self.company, source="manual")
        second_batch = AtlasImporterService.import_rows(rows=rows, company=self.company, source="manual")

        self.assertEqual(first_batch.created_opportunities, 1)
        self.assertEqual(second_batch.created_opportunities, 0)
        self.assertEqual(second_batch.skipped_duplicates, 1)
        self.assertEqual(CommercialOpportunity.objects.filter(company_name="Hospital Norte").count(), 1)

    def test_records_error_for_invalid_row_without_breaking_batch(self):
        rows = self._valid_rows()
        rows.append({"company_name": "Empresa Com Erro", "segment": "Industrial", "notes": "falha de processamento"})
        original_build = OpportunityBuilderService.build_from_analysis

        def build_side_effect(*, analysis, company, source, **kwargs):
            if analysis.opportunity.get("company_name") == "Empresa Com Erro":
                raise ValueError("Linha invalida para processamento Atlas.")
            return original_build(analysis=analysis, company=company, source=source, **kwargs)

        with patch.object(OpportunityBuilderService, "build_from_analysis", side_effect=build_side_effect):
            batch = AtlasImporterService.import_rows(rows=rows, company=self.company, source="manual")

        self.assertEqual(batch.processed_rows, 3)
        self.assertEqual(batch.created_opportunities, 2)
        self.assertEqual(len(batch.errors), 1)
        self.assertEqual(batch.errors[0]["company_name"], "Empresa Com Erro")
        self.assertEqual(batch.status, AtlasProspectImportBatch.Status.COMPLETED)

    def test_batch_counters_are_correct(self):
        rows = self._valid_rows() + [{"company_name": ""}, {"segment": "vazio"}]

        batch = AtlasImporterService.import_rows(
            rows=rows,
            company=self.company,
            source="manual",
            filename="prospects.csv",
            created_by=self.user,
        )

        self.assertEqual(batch.filename, "prospects.csv")
        self.assertEqual(batch.source, "manual")
        self.assertEqual(batch.total_rows, 4)
        self.assertEqual(batch.processed_rows, 2)
        self.assertEqual(batch.skipped_empty_rows, 2)
        self.assertEqual(batch.created_opportunities, 2)

    def test_does_not_create_lead_automatically(self):
        leads_before = Lead.objects.count()

        AtlasImporterService.import_rows(rows=self._valid_rows(), company=self.company, source="manual")

        self.assertEqual(Lead.objects.count(), leads_before)
        self.assertFalse(CommercialOpportunity.objects.filter(lead__isnull=False).exists())

    def test_does_not_send_email(self):
        with patch("django.core.mail.send_mail") as send_mail_mock:
            AtlasImporterService.import_rows(rows=self._valid_rows(), company=self.company, source="manual")

        self.assertEqual(send_mail_mock.call_count, 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_preserves_institutional_contact_fields(self):
        AtlasImporterService.import_rows(rows=self._valid_rows()[:1], company=self.company, source="manual")

        opportunity = CommercialOpportunity.objects.get(company_name="Hospital Norte")
        contacts = opportunity.metadata.get("institutional_contacts") or []

        self.assertIn("contato@hospital-norte.example.com", contacts)
        self.assertIn("+55 11 99999-0000", contacts)
        self.assertEqual(opportunity.metadata.get("contact_name"), "Maria Silva")
        self.assertEqual(opportunity.metadata.get("contact_email"), "contato@hospital-norte.example.com")
        self.assertEqual(opportunity.metadata.get("contact_phone"), "+55 11 99999-0000")

    def test_normalizes_city_and_state(self):
        rows = [
            {
                "company_name": "Fabrica Sul",
                "city": "porto alegre",
                "state": "rs",
                "notes": "necessidade de automacao industrial",
            }
        ]

        AtlasImporterService.import_rows(rows=rows, company=self.company, source="manual")
        opportunity = CommercialOpportunity.objects.get(company_name="Fabrica Sul")

        self.assertEqual(opportunity.city, "Porto Alegre")
        self.assertEqual(opportunity.state, "RS")

    def test_keeps_outreach_status_as_not_started(self):
        AtlasImporterService.import_rows(rows=self._valid_rows()[:1], company=self.company, source="manual")

        opportunity = CommercialOpportunity.objects.get(company_name="Hospital Norte")

        self.assertEqual(opportunity.outreach_status, CommercialOpportunity.OutreachStatus.NOT_STARTED)
        self.assertEqual(opportunity.outreach_channel, CommercialOpportunity.OutreachChannel.NONE)

    def test_stores_future_commercial_sender_without_sending_message(self):
        AtlasImporterService.import_rows(rows=self._valid_rows()[:1], company=self.company, source="manual")

        opportunity = CommercialOpportunity.objects.get(company_name="Hospital Norte")

        self.assertEqual(opportunity.outreach_sender_email, AtlasImporterService.OUTREACH_SENDER_EMAIL)
        self.assertEqual(opportunity.outreach_domain, AtlasImporterService.OUTREACH_DOMAIN)
        self.assertNotIn("smartcontrolbrasil.com.br", opportunity.outreach_sender_email)
        self.assertTrue(opportunity.metadata.get("outreach_prepared"))

    def test_import_csv_uses_csv_source(self):
        csv_content = (
            "company_name,segment,city,state,contact_email,notes\n"
            "Clinica Oeste,Clinica,Curitiba,PR,contato@clinica-oeste.test,limpeza hospitalar\n"
        )

        batch = AtlasImporterService.import_csv(
            file_content=csv_content,
            company=self.company,
            filename="clinicas.csv",
            created_by=self.user,
        )

        self.assertEqual(batch.source, CommercialOpportunity.Source.CSV)
        self.assertEqual(batch.created_opportunities, 1)
        opportunity = CommercialOpportunity.objects.get(company_name="Clinica Oeste")
        self.assertEqual(opportunity.source, CommercialOpportunity.Source.CSV)


class AtlasImporterApiTests(APITestCase):
    def setUp(self):
        self.user = UserFactory(email="atlas-import-api@smart360.local", password="StrongPass123", is_staff=True, is_superuser=True)
        self.company = CompanyFactory(name="Atlas API Import", slug="atlas-api-import")
        Membership.objects.create(user=self.user, company=self.company, is_primary=True)
        self.client.force_authenticate(self.user)

    def test_internal_api_imports_json_rows(self):
        payload = {
            "company": self.company.id,
            "source": "manual",
            "filename": "api-import.json",
            "rows": [
                {
                    "company_name": "Escola Modelo",
                    "segment": "Educacao",
                    "city": "Campinas",
                    "state": "SP",
                    "contact_email": "direcao@escola-modelo.test",
                    "notes": "interesse em robotica educacional",
                }
            ],
        }

        response = self.client.post(reverse("ai-agent-atlas-import-prospects"), payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["created_opportunities"], 1)
        self.assertEqual(response.data["status"], AtlasProspectImportBatch.Status.COMPLETED)
        opportunity = CommercialOpportunity.objects.get(company_name="Escola Modelo")
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.READY_FOR_REVIEW)
        self.assertIsNone(opportunity.lead)

    def test_internal_api_reports_partial_batch_errors(self):
        payload = {
            "company": self.company.id,
            "source": "google_maps",
            "filename": "api-partial.json",
            "rows": [
                {
                    "company_name": "Escola Valida",
                    "segment": "Educacao",
                    "city": "Sao Paulo",
                    "state": "SP",
                    "contact_email": "direcao@escola-valida.test",
                    "notes": "interesse em robotica educacional",
                },
                {
                    "company_name": "Escola Com Erro",
                    "segment": "Educacao",
                    "notes": "falha controlada",
                },
                {
                    "segment": "Sem nome",
                    "city": "Campinas",
                },
            ],
        }
        original_build = OpportunityBuilderService.build_from_analysis

        def build_side_effect(*, analysis, company, source, **kwargs):
            if analysis.opportunity.get("company_name") == "Escola Com Erro":
                raise ValueError("Linha invalida para processamento Atlas.")
            return original_build(analysis=analysis, company=company, source=source, **kwargs)

        with patch.object(OpportunityBuilderService, "build_from_analysis", side_effect=build_side_effect):
            response = self.client.post(reverse("ai-agent-atlas-import-prospects"), payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["status"], AtlasProspectImportBatch.Status.COMPLETED)
        self.assertEqual(response.data["created_opportunities"], 1)
        self.assertEqual(response.data["skipped_empty_rows"], 1)
        self.assertEqual(len(response.data["errors"]), 1)
        self.assertEqual(response.data["errors"][0]["company_name"], "Escola Com Erro")
        self.assertEqual(CommercialOpportunity.objects.filter(company_name="Escola Valida").count(), 1)
        self.assertFalse(CommercialOpportunity.objects.filter(company_name="Escola Com Erro").exists())
