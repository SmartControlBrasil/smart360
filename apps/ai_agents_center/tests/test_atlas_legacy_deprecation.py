import inspect
from pathlib import Path

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.ai_agents_center.models import AtlasLead, CommercialOpportunity
from apps.ai_decision_engine.services import handlers as decision_handlers
from apps.atlas_agent.api_client import ATLAS_IMPORT_PATH, AtlasAPIClient
from apps.atlas_agent.models import Lead as AtlasStandaloneLead
from apps.companies.models import Membership
from apps.growth_engine.models import Lead
from tests.factories.core import CompanyFactory, UserFactory


class AtlasLegacyDeprecationApiTests(APITestCase):
    def setUp(self):
        self.user = UserFactory(
            email="atlas-legacy-deprecation@smart360.local",
            password="StrongPass123",
            is_staff=True,
            is_superuser=True,
        )
        self.company = CompanyFactory(name="Atlas Legacy Deprecation", slug="atlas-legacy-deprecation")
        Membership.objects.create(user=self.user, company=self.company, is_primary=True)

    @override_settings(ATLAS_API_TOKEN="secure-legacy-token")
    def test_legacy_endpoint_is_deprecated_and_does_not_create_atlas_lead(self):
        payload = {
            "razao_social": "Escola Legada",
            "segmento": "Escola / Educação",
            "cidade": "Sao Paulo",
            "email_contato": "contato@escola-legada.test",
            "score": 9,
        }

        response = self.client.post(
            reverse("ai-agent-atlas-leads-ingest"),
            payload,
            format="json",
            HTTP_AUTHORIZATION="Bearer secure-legacy-token",
        )

        self.assertEqual(response.status_code, 410)
        self.assertTrue(response.data["deprecated"])
        self.assertEqual(response.data["official_endpoint"], "/api/v1/ai-agents/atlas/import-prospects/")
        self.assertEqual(AtlasLead.objects.count(), 0)
        self.assertEqual(CommercialOpportunity.objects.count(), 0)
        self.assertEqual(Lead.objects.count(), 0)

    @override_settings(DEBUG=False, ATLAS_API_TOKEN="mock-token")
    def test_legacy_endpoint_rejects_default_or_mock_token_in_production(self):
        response = self.client.post(
            reverse("ai-agent-atlas-leads-ingest"),
            {"razao_social": "Token Inseguro"},
            format="json",
            HTTP_AUTHORIZATION="Bearer mock-token",
        )

        self.assertEqual(response.status_code, 503)
        self.assertTrue(response.data["deprecated"])
        self.assertIn("secure ATLAS_API_TOKEN", response.data["detail"])
        self.assertEqual(AtlasLead.objects.count(), 0)

    def test_official_import_creates_commercial_opportunity(self):
        self.client.force_authenticate(self.user)
        payload = {
            "company": self.company.id,
            "source": "google_maps",
            "filename": "atlas-03.json",
            "rows": [
                {
                    "company_name": "Clinica Oficial Atlas",
                    "segment": "Clinica",
                    "city": "Campinas",
                    "state": "SP",
                    "contact_email": "contato@clinica-oficial.test",
                    "notes": "Fila oficial CommercialOpportunity.",
                }
            ],
        }

        response = self.client.post(reverse("ai-agent-atlas-import-prospects"), payload, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["created_opportunities"], 1)
        opportunity = CommercialOpportunity.objects.get(company_name="Clinica Oficial Atlas")
        self.assertEqual(opportunity.status, CommercialOpportunity.Status.READY_FOR_REVIEW)
        self.assertEqual(AtlasLead.objects.count(), 0)
        self.assertEqual(Lead.objects.count(), 0)


class AtlasLegacyDeprecationSourceTests(TestCase):
    def test_standalone_api_client_uses_official_import_prospects_endpoint(self):
        self.assertEqual(ATLAS_IMPORT_PATH, "/api/v1/ai-agents/atlas/import-prospects/")
        self.assertNotIn("atlas-leads/ingest", ATLAS_IMPORT_PATH)

        class Session:
            def __init__(self):
                self.calls = []

            def post(self, *args, **kwargs):
                self.calls.append((args, kwargs))

                class Response:
                    def raise_for_status(self):
                        return None

                    def json(self):
                        return {
                            "public_id": "batch",
                            "status": "completed",
                            "created_opportunities": 1,
                            "skipped_duplicates": 0,
                            "errors": [],
                        }

                return Response()

        session = Session()
        client = AtlasAPIClient(
            base_url="https://smart360.test/",
            token="secure-token",
            company_id=42,
            session=session,
        )
        client.import_prospects([AtlasStandaloneLead("Escola Oficial", "Sao Paulo", "Centro", lead_score=8)])

        self.assertEqual(session.calls[0][0][0], "https://smart360.test/api/v1/ai-agents/atlas/import-prospects/")
        self.assertNotIn("atlas-leads/ingest", session.calls[0][0][0])

    def test_decision_engine_handlers_do_not_use_legacy_atlas_models(self):
        source = inspect.getsource(decision_handlers)

        self.assertIn("CommercialOpportunity", source)
        self.assertNotIn("AtlasLead", source)
        self.assertNotIn("PendingAtlasLead", source)

    def test_admin_shell_atlas_screen_uses_commercial_opportunity(self):
        from apps.admin_shell.views import AtlasCommercialOpportunityActionView, AtlasCommercialOpportunityListView

        sources = [
            inspect.getsource(AtlasCommercialOpportunityListView),
            inspect.getsource(AtlasCommercialOpportunityActionView),
            Path("apps/admin_shell/templates/admin_shell/atlas_opportunities.html").read_text(),
        ]
        combined = "\n".join(sources)

        self.assertIn("CommercialOpportunity", combined)
        self.assertNotIn("AtlasLead", combined)
        self.assertNotIn("PendingAtlasLead", combined)

    def test_commercial_opportunity_still_points_to_growth_engine_lead(self):
        lead_field = CommercialOpportunity._meta.get_field("lead")

        self.assertEqual(lead_field.related_model, Lead)
        self.assertEqual(lead_field.related_model._meta.app_label, "growth_engine")
