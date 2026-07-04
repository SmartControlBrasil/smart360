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

    @patch("apps.atlas_agent.main.SchoolScraper")
    @patch("apps.atlas_agent.main.EnrichmentService")
    @patch("apps.atlas_agent.main.ScoringEngine")
    def test_post_run_mock_without_cwd_permissions_does_not_crash(self, mock_scoring, mock_enricher, mock_scraper):
        lead = StandaloneLead("Escola Vila", "Sao Paulo", "Vila Mariana", lead_score=80)
        mock_scraper.return_value.run_pipeline.return_value = [lead]
        mock_enricher.return_value.process_lead.side_effect = lambda l: l
        mock_scoring.return_value.process_lead.side_effect = lambda l: l

        with patch.dict(os.environ, {
            "ATLAS_CSV_OUTPUT_PATH": "/root/readonly_directory_for_test/leads.csv",
            "ATLAS_API_TOKEN": "mock-token",
            "ATLAS_WRITE_CSV_OUTPUT": "true"
        }):
            response = self.client.post(reverse("admin-shell:atlas-run"), {
                "action": "run",
                "segment": "escola particular",
                "city": "Vila Mariana",
                "source": "mock",
                "max_prospects_per_run": "5",
                "min_score": "5",
            })

        # Failure to write output CSV should be logged as warning, and pipeline should complete successfully (return 200 with summary)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resumo da Execução")

    @patch("apps.atlas_agent.main.EnrichmentService")
    @patch("apps.atlas_agent.main.ScoringEngine")
    def test_post_run_mock_with_missing_explicit_input_csv_returns_controlled_error(self, mock_scoring, mock_enricher):
        mock_enricher.return_value.process_lead.side_effect = lambda l: l
        mock_scoring.return_value.process_lead.side_effect = lambda l: l

        with patch.dict(os.environ, {
            "ATLAS_MOCK_CSV_PATH": "non_existent_file_for_test.csv",
            "ATLAS_API_TOKEN": "mock-token"
        }):
            response = self.client.post(reverse("admin-shell:atlas-run"), {
                "action": "run",
                "segment": "escola particular",
                "city": "Vila Mariana",
                "source": "mock",
                "max_prospects_per_run": "5",
                "min_score": "5",
            })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Falha na Configuração")
        self.assertContains(response, "Arquivo mock indisponível ou sem permissão")
        self.assertNotContains(response, "Erro inesperado")

    @patch("apps.atlas_agent.main.SchoolScraper")
    @patch("apps.atlas_agent.main.EnrichmentService")
    @patch("apps.atlas_agent.main.ScoringEngine")
    @patch("apps.atlas_agent.api_client.requests.Session")
    def test_post_run_mock_with_different_cwd_and_absolute_resolution(self, mock_session_cls, mock_scoring, mock_enricher, mock_scraper):
        import tempfile
        import shutil
        from pathlib import Path
        from apps.atlas_agent import main as atlas_main
        
        # Setup mocks
        lead = StandaloneLead("Escola Cwd Test", "Sao Paulo", "Vila Mariana", lead_score=80)
        mock_scraper.return_value.run_pipeline.return_value = [lead]
        mock_enricher.return_value.process_lead.side_effect = lambda l: l
        mock_scoring.return_value.process_lead.side_effect = lambda l: l

        api_response = Mock()
        api_response.json.return_value = {
            "public_id": "batch-cwd-123",
            "status": "completed",
            "processed_rows": 1,
            "created_opportunities": 1,
            "skipped_duplicates": 0,
            "errors": [],
        }
        session = Mock()
        session.post.return_value = api_response
        mock_session_cls.return_value = session

        # Save current CWD
        old_cwd = os.getcwd()
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Change directory to a temp folder to simulate running from Gunicorn / different CWD
            os.chdir(temp_dir)
            
            # Target output file path (relative filename)
            relative_target_name = "test_leads_cwd_override.csv"
            expected_absolute_dir = Path(atlas_main.__file__).resolve().parent
            expected_absolute_file = expected_absolute_dir / relative_target_name
            
            # Remove output file if exists
            if expected_absolute_file.exists():
                os.remove(expected_absolute_file)

            with patch.dict(os.environ, {
                "ATLAS_MOCK_CSV_PATH": relative_target_name,
                "ATLAS_API_TOKEN": "real-safe-token-for-test",
                "ATLAS_WRITE_CSV_OUTPUT": "true"
            }):
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
            
            # Assert file was written to apps/atlas_agent/ folder, NOT to the temp_dir CWD!
            self.assertTrue(expected_absolute_file.exists())
            self.assertFalse((Path(temp_dir) / relative_target_name).exists())
            
            # Clean up output file
            if expected_absolute_file.exists():
                os.remove(expected_absolute_file)
                
        finally:
            os.chdir(old_cwd)
            shutil.rmtree(temp_dir)

