from io import StringIO
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.atlas_agent.api_client import ATLAS_IMPORT_PATH, qualified_prospects
from apps.atlas_agent.config import AtlasConfigError, AtlasPocConfig, DEFAULT_MAX_PROSPECTS_PER_RUN
from apps.atlas_agent.main import main, run_pipeline
from apps.atlas_agent.models import Lead


class AtlasPocConfigTests(SimpleTestCase):
    def test_production_without_token_fails(self):
        with self.assertRaises(AtlasConfigError) as ctx:
            AtlasPocConfig.from_env({
                "ATLAS_ENV": "production",
                "ATLAS_API_BASE_URL": "https://smart360.test",
                "ATLAS_COMPANY_ID": "1",
                "GOOGLE_PLACES_API_KEY": "places-key"
            })

        self.assertIn("ATLAS_API_TOKEN", str(ctx.exception))

    def test_production_without_google_places_key_fails(self):
        with self.assertRaises(AtlasConfigError) as ctx:
            AtlasPocConfig.from_env({
                "ATLAS_ENV": "production",
                "ATLAS_API_BASE_URL": "https://smart360.test",
                "ATLAS_API_TOKEN": "real-token",
                "ATLAS_COMPANY_ID": "1"
            })

        self.assertIn("GOOGLE_PLACES_API_KEY", str(ctx.exception))

    def test_excessive_max_prospects_limit_fails(self):
        with self.assertRaises(AtlasConfigError) as ctx:
            AtlasPocConfig.from_env({
                "ATLAS_ENV": "development",
                "ATLAS_MAX_PROSPECTS_PER_RUN": "51"
            })

        self.assertIn("excede o limite seguro de 50 prospects", str(ctx.exception))

    def test_production_with_mock_token_fails(self):
        with self.assertRaises(AtlasConfigError) as ctx:
            AtlasPocConfig.from_env(
                {
                    "ATLAS_ENV": "production",
                    "ATLAS_API_BASE_URL": "https://smart360.test",
                    "ATLAS_API_TOKEN": "mock-token",
                    "ATLAS_COMPANY_ID": "1",
                    "GOOGLE_PLACES_API_KEY": "places-key",
                }
            )

        self.assertIn("inseguro", str(ctx.exception))

    def test_development_allows_mock_fallback(self):
        config = AtlasPocConfig.from_env({"ATLAS_ENV": "development"})

        self.assertEqual(config.max_prospects_per_run, DEFAULT_MAX_PROSPECTS_PER_RUN)
        self.assertTrue(config.mock_mode)
        self.assertFalse(config.can_sync_api)
        self.assertFalse(config.enable_mailer)

    def test_main_returns_error_code_for_critical_config_error(self):
        with patch("sys.stdout", new_callable=StringIO) as stdout:
            code = main(
                {
                    "ATLAS_ENV": "production",
                    "ATLAS_API_BASE_URL": "https://smart360.test",
                    "ATLAS_API_TOKEN": "mock-token",
                    "ATLAS_COMPANY_ID": "1",
                    "GOOGLE_PLACES_API_KEY": "places-key",
                }
            )

        self.assertEqual(code, 2)
        self.assertIn("erro critico", stdout.getvalue())
        self.assertNotIn("mock-token", stdout.getvalue())


class AtlasPocControlledRunTests(SimpleTestCase):
    def _lead(self, name, score=8):
        return Lead(
            institution_name=name,
            city="Sao Paulo",
            region="Vila Mariana",
            website_domain=f"{name.lower().replace(' ', '-')}.test",
            contact_email=f"contato@{name.lower().replace(' ', '-')}.test",
            decider_name="Maria",
            lead_score=score,
        )

    def test_limit_max_prospects_per_run_is_respected(self):
        raw_leads = [self._lead(f"Escola {idx}") for idx in range(5)]
        config = AtlasPocConfig.from_env({"ATLAS_ENV": "development", "ATLAS_MAX_PROSPECTS_PER_RUN": "2"})

        with patch("apps.atlas_agent.main.SchoolScraper") as scraper_cls,              patch("apps.atlas_agent.main.EnrichmentService") as enricher_cls,              patch("apps.atlas_agent.main.ScoringEngine") as scoring_cls,              patch("apps.atlas_agent.main._write_csv"):
            scraper_cls.return_value.run_pipeline.return_value = raw_leads
            enricher_cls.return_value.process_lead.side_effect = lambda lead: lead
            scoring_cls.return_value.process_lead.side_effect = lambda lead: lead

            summary = run_pipeline(config)

        self.assertEqual(summary.collected, 5)
        self.assertEqual(summary.enriched, 2)
        self.assertEqual(summary.qualified, 2)
        self.assertEqual(enricher_cls.return_value.process_lead.call_count, 2)

    def test_main_and_api_client_use_only_import_prospects(self):
        self.assertEqual(ATLAS_IMPORT_PATH, "/api/v1/ai-agents/atlas/import-prospects/")
        self.assertNotIn("atlas-leads/ingest", ATLAS_IMPORT_PATH)

        raw_leads = [self._lead("Escola Oficial")]
        config = AtlasPocConfig.from_env(
            {
                "ATLAS_ENV": "production",
                "ATLAS_API_BASE_URL": "https://smart360.test",
                "ATLAS_API_TOKEN": "real-token",
                "ATLAS_COMPANY_ID": "42",
                "GOOGLE_PLACES_API_KEY": "places-key",
                "APOLLO_API_KEY": "apollo-key",
            }
        )
        response = Mock()
        response.json.return_value = {
            "public_id": "batch-1",
            "status": "completed",
            "created_opportunities": 1,
            "skipped_duplicates": 0,
            "errors": [],
        }
        session = Mock()
        session.post.return_value = response

        with patch("apps.atlas_agent.main.SchoolScraper") as scraper_cls,              patch("apps.atlas_agent.main.EnrichmentService") as enricher_cls,              patch("apps.atlas_agent.main.ScoringEngine") as scoring_cls,              patch("apps.atlas_agent.api_client.requests.Session", return_value=session),              patch("apps.atlas_agent.main._write_csv"):
            scraper_cls.return_value.run_pipeline.return_value = raw_leads
            enricher_cls.return_value.process_lead.side_effect = lambda lead: lead
            scoring_cls.return_value.process_lead.side_effect = lambda lead: lead

            summary = run_pipeline(config)

        self.assertEqual(summary.sent_to_api, 1)
        self.assertEqual(session.post.call_args.args[0], "https://smart360.test/api/v1/ai-agents/atlas/import-prospects/")
        self.assertNotIn("atlas-leads/ingest", session.post.call_args.args[0])

    def test_mailer_is_not_called(self):
        raw_leads = [self._lead("Escola Sem Email")]
        config = AtlasPocConfig.from_env({"ATLAS_ENV": "development"})

        with patch("apps.atlas_agent.main.SchoolScraper") as scraper_cls,              patch("apps.atlas_agent.main.EnrichmentService") as enricher_cls,              patch("apps.atlas_agent.main.ScoringEngine") as scoring_cls,              patch("apps.atlas_agent.mailer.ColdMailer") as mailer_cls,              patch("apps.atlas_agent.main._write_csv"):
            scraper_cls.return_value.run_pipeline.return_value = raw_leads
            enricher_cls.return_value.process_lead.side_effect = lambda lead: lead
            scoring_cls.return_value.process_lead.side_effect = lambda lead: lead

            run_pipeline(config)

        mailer_cls.assert_not_called()

    def test_summary_does_not_expose_token_or_api_keys(self):
        raw_leads = [self._lead("Escola Segura")]
        config = AtlasPocConfig.from_env(
            {
                "ATLAS_ENV": "development",
                "ATLAS_API_BASE_URL": "https://smart360.test",
                "ATLAS_API_TOKEN": "super-secret-token",
                "ATLAS_COMPANY_ID": "42",
                "GOOGLE_PLACES_API_KEY": "places-secret",
                "APOLLO_API_KEY": "apollo-secret",
            }
        )
        response = Mock()
        response.json.return_value = {
            "public_id": "batch-1",
            "status": "completed",
            "created_opportunities": 1,
            "skipped_duplicates": 0,
            "errors": [],
        }
        session = Mock()
        session.post.return_value = response

        with patch("apps.atlas_agent.main.SchoolScraper") as scraper_cls,              patch("apps.atlas_agent.main.EnrichmentService") as enricher_cls,              patch("apps.atlas_agent.main.ScoringEngine") as scoring_cls,              patch("apps.atlas_agent.api_client.requests.Session", return_value=session),              patch("apps.atlas_agent.main._write_csv"),              patch("sys.stdout", new_callable=StringIO) as stdout:
            scraper_cls.return_value.run_pipeline.return_value = raw_leads
            enricher_cls.return_value.process_lead.side_effect = lambda lead: lead
            scoring_cls.return_value.process_lead.side_effect = lambda lead: lead

            run_pipeline(config)

        output = stdout.getvalue()
        self.assertIn("resumo final", output)
        self.assertNotIn("super-secret-token", output)
        self.assertNotIn("places-secret", output)
        self.assertNotIn("apollo-secret", output)

    def test_scoring_filters_below_minimum_score(self):
        low_score = self._lead("Escola Baixa", score=4)
        high_score = self._lead("Escola Alta", score=8)

        self.assertEqual(qualified_prospects([low_score, high_score], minimum_score=5), [high_score])

    @patch("apps.atlas_agent.scraper.requests.get")
    @patch("apps.atlas_agent.enricher.requests.post")
    def test_mock_run_does_not_make_external_api_calls(self, mock_post, mock_get):
        config = AtlasPocConfig.from_env({"ATLAS_ENV": "development"})
        with patch("apps.atlas_agent.main._write_csv"):
            summary = run_pipeline(config)

        self.assertTrue(config.mock_mode)
        mock_get.assert_not_called()
        mock_post.assert_not_called()
        self.assertEqual(summary.collected, 2)
        self.assertEqual(summary.enriched, 2)

    def test_runbook_contains_real_run_checklist(self):
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        runbook_path = os.path.abspath(os.path.join(current_dir, "../../../docs/atlas_poc_runbook.md"))
        self.assertTrue(os.path.exists(runbook_path), f"Runbook nao encontrado no caminho: {runbook_path}")
        with open(runbook_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("## Rodada real manual com Google Places", content)
        self.assertIn("- [ ] Validar a configuração do ambiente usando o comando de pré-validação.", content)
        self.assertIn("- [ ] Confirmar que `ATLAS_ENV=production` está definido no ambiente.", content)
        self.assertIn("- [ ] Confirmar que a chave `GOOGLE_PLACES_API_KEY` é válida e ativa.", content)
        self.assertIn("- [ ] Confirmar que o `ATLAS_API_TOKEN` é seguro (não usar tokens inseguros como `mock-token`).", content)
        self.assertIn("- [ ] Confirmar que o `ATLAS_COMPANY_ID` aponta para o ID da empresa correta.", content)
        self.assertIn("- [ ] Verificar que o limite `ATLAS_MAX_PROSPECTS_PER_RUN` está definido para um valor seguro (máximo 10 no piloto).", content)
        self.assertIn("- [ ] Garantir que cold mail e envio de e-mails permanecem desabilitados (`ATLAS_ENABLE_MAILER=false`).", content)
        self.assertIn("## Critérios de sucesso do piloto", content)
        self.assertIn("- Quantidade coletada.", content)
        self.assertIn("- Quantidade enriquecida.", content)
        self.assertIn("- Quantidade acima do score mínimo.", content)
        self.assertIn("- Quantidade importada para `CommercialOpportunity`.", content)
        self.assertIn("- Duplicados ignorados pela API oficial.", content)
        self.assertIn("- Oportunidades prontas para revisão.", content)
        self.assertIn("- Oportunidades aprovadas.", content)
        self.assertIn("- Leads convertidos após revisão humana.", content)
        self.assertIn("- Zero e-mails enviados.", content)

    @patch("apps.atlas_agent.main.run_pipeline")
    def test_validate_only_mode_does_not_execute_pipeline(self, mock_run_pipeline):
        with patch("sys.stdout", new_callable=StringIO) as stdout:
            code = main({
                "ATLAS_VALIDATE_ONLY": "true",
                "ATLAS_ENV": "production",
                "ATLAS_API_BASE_URL": "https://smart360.test",
                "ATLAS_API_TOKEN": "real-token",
                "ATLAS_COMPANY_ID": "1",
                "GOOGLE_PLACES_API_KEY": "places-key"
            })
        self.assertEqual(code, 0)
        self.assertIn("Modo Pre-Validacao", stdout.getvalue())
        self.assertIn("APTA para rodada real", stdout.getvalue())
        mock_run_pipeline.assert_not_called()

    def test_runbook_contains_real_run_manual_section(self):
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        runbook_path = os.path.abspath(os.path.join(current_dir, "../../../docs/atlas_poc_runbook.md"))
        self.assertTrue(os.path.exists(runbook_path), f"Runbook nao encontrado no caminho: {runbook_path}")
        with open(runbook_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("## Rodada real manual com Google Places", content)
        self.assertIn("### Checklist Antes de Executar", content)
        self.assertIn("### Variáveis Obrigatórias", content)
        self.assertIn("### Comando de Pré-Validação", content)
        self.assertIn("### Comando de Execução Real Manual", content)
        self.assertIn("### Limites Recomendados", content)
        self.assertIn("### Onde Revisar Oportunidades", content)
        self.assertIn("### Como Interromper em Caso de Erro", content)
        self.assertIn("### Política LGPD e Conformidade", content)



from django.test import TestCase
from tests.factories.core import CompanyFactory, UserFactory
from apps.companies.models import Membership
from apps.ai_agents_center.services.atlas_importer import AtlasImporterService
from apps.ai_agents_center.models import CommercialOpportunity

class AtlasPocDatabaseTests(TestCase):
    def setUp(self):
        self.user = UserFactory(email="atlas-poc@smart360.local", password="StrongPass123", is_staff=True, is_superuser=True)
        self.company = CompanyFactory(name="Atlas PoC Company", slug="atlas-poc-company")
        Membership.objects.create(user=self.user, company=self.company, is_primary=True)

    def test_repeated_execution_does_not_explode_on_duplicates(self):
        rows = [
            {
                "company_name": "Escola Duplicada",
                "segment": "escola particular",
                "city": "Sao Paulo",
                "state": "SP",
                "website": "escola-duplicada.test",
                "contact_email": "direcao@escola-duplicada.test",
                "notes": "Alto fluxo de limpeza",
            }
        ]

        # First import
        batch_1 = AtlasImporterService.import_rows(
            rows=rows,
            company=self.company,
            source="google_maps",
            created_by=self.user,
        )
        self.assertEqual(batch_1.created_opportunities, 1)
        self.assertEqual(batch_1.skipped_duplicates, 0)
        self.assertEqual(CommercialOpportunity.objects.count(), 1)

        # Second import (repeated execution)
        batch_2 = AtlasImporterService.import_rows(
            rows=rows,
            company=self.company,
            source="google_maps",
            created_by=self.user,
        )
        self.assertEqual(batch_2.created_opportunities, 0)
        self.assertEqual(batch_2.skipped_duplicates, 1)
        # Verify no database/duplicity exceptions were raised, and it was handled gracefully
        self.assertEqual(CommercialOpportunity.objects.count(), 1)
