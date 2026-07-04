from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.urls import reverse

from apps.atlas_agent.api_client import (
    ATLAS_IMPORT_PATH,
    AtlasAPIClient,
    prospect_to_api_row,
    qualified_prospects,
)
from apps.atlas_agent.enricher import EnrichmentService
from apps.atlas_agent.mailer import ColdMailer
from apps.atlas_agent.models import Lead


class AtlasStandaloneIntegrationTests(SimpleTestCase):
    def test_official_import_route_uses_versioned_api_prefix(self):
        self.assertEqual(
            reverse("ai-agent-atlas-import-prospects"),
            ATLAS_IMPORT_PATH,
        )

    def test_score_reflects_prospect_completeness(self):
        sparse = Lead(
            institution_name="Escola Base",
            city="Sao Paulo",
            region="Centro",
        )
        complete = Lead(
            institution_name="Escola Completa",
            city="Sao Paulo",
            region="Centro",
            website_domain="escola.test",
            phone="11999990000",
            decider_name="Maria",
            decider_role="Diretora",
            contact_email="maria@escola.test",
            notes="Endereco confirmado em fonte publica.",
        )

        self.assertEqual(EnrichmentService.calculate_lead_score(sparse), 2)
        self.assertEqual(EnrichmentService.calculate_lead_score(complete), 10)

    def test_minimum_score_filters_unqualified_prospects(self):
        low_score = Lead("Escola A", "Sao Paulo", "Centro", lead_score=4)
        qualified = Lead("Escola B", "Sao Paulo", "Centro", lead_score=5)

        self.assertEqual(qualified_prospects([low_score, qualified]), [qualified])


    def test_poc_payload_targets_review_queue_without_email_fields(self):
        lead = Lead(
            institution_name="Escola Sem Envio",
            city="Sao Paulo",
            region="Vila Mariana",
            website_domain="escola-sem-envio.test",
            contact_email="direcao@escola-sem-envio.test",
            lead_score=7,
        )

        row = prospect_to_api_row(lead)

        self.assertEqual(row["company_name"], "Escola Sem Envio")
        self.assertEqual(row["source"], "google_maps")
        self.assertIn("Score comercial Atlas: 7/100. Qualidade dos dados: 0/10.", row["notes"])
        self.assertNotIn("lead_status", row)
        self.assertNotIn("send_email", row)
        self.assertNotIn("outreach_status", row)

    def test_client_posts_prospects_to_official_endpoint(self):
        response = Mock()
        response.json.return_value = {
            "public_id": "batch-123",
            "status": "completed",
            "processed_rows": 1,
            "created_opportunities": 1,
            "skipped_duplicates": 0,
            "errors": [],
        }
        session = Mock()
        session.post.return_value = response
        lead = Lead(
            institution_name="Escola Modelo",
            city="Sao Paulo",
            region="Vila Mariana",
            website_domain="escola-modelo.test",
            contact_email="direcao@escola-modelo.test",
            lead_score=8,
        )
        client = AtlasAPIClient(
            base_url="https://smart360.test/",
            token="secret-token",
            company_id=42,
            session=session,
        )

        result = client.import_prospects([lead])

        self.assertEqual(result.created_opportunities, 1)
        self.assertEqual(result.processed_rows, 1)
        response.raise_for_status.assert_called_once_with()
        request = session.post.call_args
        self.assertEqual(
            request.args[0],
            "https://smart360.test/api/v1/ai-agents/atlas/import-prospects/",
        )
        self.assertEqual(request.kwargs["headers"]["Authorization"], "Bearer secret-token")
        self.assertEqual(request.kwargs["json"]["company"], 42)
        self.assertEqual(request.kwargs["json"]["source"], "google_maps")
        self.assertEqual(request.kwargs["json"]["rows"], [prospect_to_api_row(lead)])
        self.assertIn("Score comercial Atlas: 8/100. Qualidade dos dados: 0/10.", request.kwargs["json"]["rows"][0]["notes"])


    def test_client_preserves_partial_import_errors(self):
        response = Mock()
        response.json.return_value = {
            "public_id": "batch-456",
            "status": "completed",
            "processed_rows": 1,
            "created_opportunities": 1,
            "skipped_duplicates": 0,
            "errors": [{"row": 2, "company_name": "Escola Com Erro", "error": "Linha invalida"}],
        }
        session = Mock()
        session.post.return_value = response
        client = AtlasAPIClient(
            base_url="https://smart360.test/",
            token="secret-token",
            company_id=42,
            session=session,
        )

        result = client.import_prospects([Lead("Escola Modelo", "Sao Paulo", "Vila Mariana", lead_score=8)])

        self.assertEqual(result.created_opportunities, 1)
        self.assertEqual(result.processed_rows, 1)
        self.assertEqual(result.errors, [{"row": 2, "company_name": "Escola Com Erro", "error": "Linha invalida"}])

    def test_cold_mailer_remains_in_dry_run_by_default(self):
        self.assertTrue(ColdMailer().dry_run)

    def test_enricher_does_not_set_commercial_score(self):
        lead = Lead(
            institution_name="Escola Inovacao",
            city="Sao Paulo",
            region="Vila Mariana",
            website_domain="escola-inovacao.test",
        )
        enricher = EnrichmentService(provider="mock")
        processed = enricher.process_lead(lead)
        # Should populate enrichment_quality_score (0-10) but NOT lead_score (which stays default 0)
        self.assertGreater(processed.enrichment_quality_score, 0)
        self.assertEqual(processed.lead_score, 0)

    def test_scoring_engine_defines_commercial_score(self):
        from apps.atlas_agent.scoring import ScoringEngine
        lead = Lead(
            institution_name="Escola Comercial",
            city="Sao Paulo",
            region="Vila Mariana",
            website_domain="escola-comercial.test",
            enrichment_quality_score=8,
        )
        scoring = ScoringEngine()
        processed = scoring.process_lead(lead)
        # lead_score should be 0-100 commercial score (in SP with decisor and escola keyword, it's high)
        self.assertGreater(processed.lead_score, 10)
        self.assertEqual(processed.enrichment_quality_score, 8)

    def test_payload_contains_separated_scores(self):
        lead = Lead(
            institution_name="Escola Total",
            city="Sao Paulo",
            region="Vila Mariana",
            lead_score=85,
            enrichment_quality_score=9,
        )
        row = prospect_to_api_row(lead)
        self.assertIn("Score comercial Atlas: 85/100", row["notes"])
        self.assertIn("Qualidade dos dados: 9/10", row["notes"])

    def test_qualified_prospects_raises_in_production_without_min_score(self):
        import os
        lead = Lead("Escola", "Sao Paulo", "Vila Mariana", lead_score=80)
        # Using patch to set environment
        with patch.dict(os.environ, {"ATLAS_ENV": "production"}):
            with self.assertRaises(ValueError) as ctx:
                qualified_prospects([lead], minimum_score=None)
            self.assertIn("exige o argumento minimum_score de forma explicita", str(ctx.exception))

