import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from apps.livia_assistant.rag.pdf_selector import score_pdf_candidate, select_pdf_candidates


class PDFSelectorTests(SimpleTestCase):
    def test_score_prioritizes_fmea_failures_reliability_and_tpm(self):
        scored = score_pdf_candidate("Manutenção/FMEA falhas confiabilidade TPM.pdf", 1024)
        self.assertGreater(scored["score"], 30)
        self.assertTrue({"fmea", "falhas", "confiabilidade", "tpm"}.issubset(scored["matched_terms"]))
        self.assertEqual(scored["recommended_category"], "manutencao")

    def test_score_reduces_priority_for_law_and_economics(self):
        technical = score_pdf_candidate("controle e automacao.pdf", 1024)["score"]
        penalized = score_pdf_candidate("direito e economia.pdf", 1024)["score"]
        self.assertGreater(technical, penalized)
        self.assertLess(penalized, 0)

    def test_select_ignores_oversized_and_returns_score_order(self):
        with TemporaryDirectory() as directory:
            base_path = Path(directory)
            (base_path / "controle.pdf").write_bytes(b"invalid pdf")
            (base_path / "FMEA falhas confiabilidade TPM.pdf").write_bytes(b"invalid pdf")
            oversized = base_path / "manutencao preditiva.pdf"
            with oversized.open("wb") as file_handle:
                file_handle.truncate(21 * 1024 * 1024)

            with patch.object(Path, "read_bytes", side_effect=AssertionError("PDF extraction is forbidden")):
                selection = select_pdf_candidates(base_path, max_size_mb=20)

        self.assertEqual(selection["total_pdfs"], 3)
        self.assertEqual(selection["oversized_count"], 1)
        self.assertEqual(selection["candidates"][0]["filename"], "FMEA falhas confiabilidade TPM.pdf")
        self.assertNotIn("manutencao preditiva.pdf", [item["filename"] for item in selection["candidates"]])


class PDFSelectorCommandTests(SimpleTestCase):
    def test_command_does_not_break_without_raw_directory(self):
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            output = StringIO()
            call_command("select_livia_pdf_candidates", stdout=output)
        self.assertIn("Pasta não encontrada", output.getvalue())

    def test_command_generates_markdown_and_json_reports(self):
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            base_path = Path(directory)
            raw_path = base_path / "knowledge" / "raw_academico" / "Manutenção"
            raw_path.mkdir(parents=True)
            (raw_path / "FMEA e falhas.pdf").write_bytes(b"invalid pdf")
            legal_path = base_path / "knowledge" / "raw_academico" / "Direito"
            legal_path.mkdir(parents=True)
            (legal_path / "direito.pdf").write_bytes(b"invalid pdf")
            output = StringIO()

            call_command("select_livia_pdf_candidates", stdout=output)

            markdown_path = base_path / "knowledge" / "reports" / "pdf_candidates.md"
            json_path = base_path / "knowledge" / "reports" / "pdf_candidates.json"
            markdown = markdown_path.read_text(encoding="utf-8")
            report = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertEqual(report["total_pdfs"], 2)
        self.assertEqual(report["candidate_count"], 1)
        self.assertIn("## Recomendação de conversão por lote", markdown)
        self.assertIn("PDFs encontrados: 2", output.getvalue())
