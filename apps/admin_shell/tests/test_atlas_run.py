import os
import unittest
from unittest.mock import Mock, patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from tests.factories.core import UserFactory, CompanyFactory
from apps.companies.models import Membership
from apps.ai_agents_center.models import CommercialOpportunity
from apps.growth_engine.models import Lead as GrowthLead
from apps.atlas_agent.models import Lead as StandaloneLead


class AtlasRunDashboardTests(TestCase):
    def setUp(self):
        self.user = UserFactory(email="operator@smart360.local", password="StrongPass123", is_staff=True, is_superuser=True)
        self.company = CompanyFactory(name="Atlas Corp", slug="atlas-corp")
        Membership.objects.create(user=self.user, company=self.company, is_primary=True)
        self.client.force_login(self.user)

    def test_atlas_run_get_loads_authorized(self):
        response = self.client.get(reverse("admin-shell:atlas-run"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin_shell/atlas_run.html")
        self.assertContains(response, "Rodar Atlas")
        self.assertContains(response, "Segmento / Termo de busca")

    def test_atlas_run_requires_authentication(self):
        self.client.logout()
        response = self.client.get(reverse("admin-shell:atlas-run"))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/admin/login/"))

    def test_menu_contains_rodar_atlas(self):
        response = self.client.get(reverse("admin-shell:atlas-opportunities"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Rodar Atlas")

    @patch("apps.atlas_agent.main.SchoolScraper")
    @patch("apps.atlas_agent.main.EnrichmentService")
    @patch("apps.atlas_agent.main.ScoringEngine")
    def test_validate_only_in_dev_mock_does_not_call_external_apis(self, mock_scoring, mock_enricher, mock_scraper):
        # Validate-only does not instantiate run_pipeline at all
        response = self.client.post(reverse("admin-shell:atlas-run"), {
            "action": "validate",
            "segment": "escola particular",
            "city": "Vila Mariana",
            "source": "mock",
            "max_prospects_per_run": "5",
            "min_score": "5",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pré-validação development/mock concluída")
        mock_scraper.assert_not_called()
        mock_enricher.assert_not_called()
        mock_scoring.assert_not_called()

    @patch("apps.atlas_agent.main.SchoolScraper")
    @patch("apps.atlas_agent.main.EnrichmentService")
    @patch("apps.atlas_agent.main.ScoringEngine")
    @patch("apps.atlas_agent.main._write_csv")
    @patch("apps.atlas_agent.api_client.requests.Session")
    def test_post_run_mock_executes_pipeline_and_shows_summary(self, mock_session_cls, mock_write_csv, mock_scoring, mock_enricher, mock_scraper):
        # Setup mocks
        lead = StandaloneLead("Escola Vila", "Sao Paulo", "Vila Mariana", lead_score=80)
        mock_scraper.return_value.run_pipeline.return_value = [lead]
        mock_enricher.return_value.process_lead.side_effect = lambda l: l
        mock_scoring.return_value.process_lead.side_effect = lambda l: l

        # Mock API Response
        api_response = Mock()
        api_response.json.return_value = {
            "public_id": "batch-mock-123",
            "status": "completed",
            "processed_rows": 1,
            "created_opportunities": 1,
            "skipped_duplicates": 0,
            "errors": [],
        }
        session = Mock()
        session.post.return_value = api_response
        mock_session_cls.return_value = session

        # Call POST run
        # Use config with a valid token so that can_sync_api evaluates to True and it hits the mocked API Client
        with patch.dict(os.environ, {"ATLAS_API_TOKEN": "real-safe-token-for-test"}):
            response = self.client.post(reverse("admin-shell:atlas-run"), {
                "action": "run",
                "segment": "escola particular",
                "city": "Vila Mariana",
                "source": "mock",
                "max_prospects_per_run": "5",
                "min_score": "5",
            })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resumo da Execução")
        self.assertContains(response, "Coletados")
        self.assertContains(response, "Enviados para API")
        self.assertContains(response, "Ver Oportunidades")
        self.assertContains(response, "Ver Importações")

        # Verify no Lead was created directly (must remain 0)
        self.assertEqual(GrowthLead.objects.count(), 0)

        # Config verify mailer
        # Let's inspect config inside the run_pipeline call.
        # But we can also check that the output summary has emails sent = 0
        self.assertContains(response, "E-mails enviados")
        self.assertContains(response, "0</strong>")

    def test_post_run_with_limit_above_10_is_blocked(self):
        response = self.client.post(reverse("admin-shell:atlas-run"), {
            "action": "run",
            "segment": "escola particular",
            "city": "Vila Mariana",
            "source": "mock",
            "max_prospects_per_run": "15",
            "min_score": "5",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "O limite máximo de prospects permitido via painel é 10.")

    @patch("apps.atlas_agent.main.SchoolScraper")
    def test_validate_only_production_google_places_fails_without_keys(self, mock_scraper):
        # production/google_places requires credentials and tokens. Should fail securely.
        with patch.dict(os.environ, {"ATLAS_ENV": "production"}):
            response = self.client.post(reverse("admin-shell:atlas-run"), {
                "action": "validate",
                "segment": "escola particular",
                "city": "Vila Mariana",
                "source": "google_places",
                "max_prospects_per_run": "5",
                "min_score": "70",
            })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Production exige")
        self.assertNotContains(response, "Configuração production validada")
