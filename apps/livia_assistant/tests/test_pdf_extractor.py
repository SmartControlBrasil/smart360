from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from apps.livia_assistant.rag.pdf_extractor import (
    build_pdf_markdown,
    convert_pdf_to_markdown,
    infer_pdf_output_category,
    normalize_pdf_text,
)


LONG_TEXT = "Conteúdo técnico sobre manutenção, falhas, confiabilidade e diagnóstico industrial. " * 20


class PDFExtractorTests(SimpleTestCase):
    def test_normalize_pdf_text_cleans_spaces_and_breaks(self):
        result = normalize_pdf_text("  Título   técnico \n\n\n Primeiro   trecho. \x00\n\n Segundo. ")
        self.assertEqual(result, "Título técnico\n\nPrimeiro trecho.\n\nSegundo.")

    def test_infer_pdf_output_categories(self):
        for path in ("FMEA.pdf", "analise de falhas.pdf", "TPM.pdf"):
            self.assertEqual(infer_pdf_output_category(path), "manutencao")
        for path in ("automação.pdf", "controle.pdf", "robótica.pdf"):
            self.assertEqual(infer_pdf_output_category(path), "engenharia")

    def test_build_pdf_markdown_includes_source_header_and_application(self):
        markdown = build_pdf_markdown("raw_academico/TPM.pdf", LONG_TEXT, "manutencao")
        self.assertIn("# TPM", markdown)
        self.assertIn("> Fonte original: raw_academico/TPM.pdf", markdown)
        self.assertIn("> Categoria: manutencao", markdown)
        self.assertIn("## Aplicação para a Smart Control Brasil", markdown)

    def test_convert_does_not_generate_markdown_for_insufficient_text(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "FMEA.pdf"
            source.write_bytes(b"fake")
            with patch("apps.livia_assistant.rag.pdf_extractor.extract_pdf_text", return_value="texto curto"):
                result = convert_pdf_to_markdown(source, Path(directory) / "knowledge")
        self.assertEqual(result["status"], "ignored")
        self.assertIsNone(result["output_path"])

    def test_convert_rejects_corrupted_extracted_text(self):
        with TemporaryDirectory() as directory:
            source = Path(directory) / "Robotica.pdf"
            source.write_bytes(b"fake")
            corrupted = "/0 /1 /2 " * 300
            with patch("apps.livia_assistant.rag.pdf_extractor.extract_pdf_text", return_value=corrupted):
                result = convert_pdf_to_markdown(source, Path(directory) / "knowledge")
        self.assertEqual(result["status"], "error")
        self.assertIn("corrupted", result["reason"])

    def test_convert_does_not_overwrite_existing_markdown(self):
        with TemporaryDirectory() as directory:
            base_path = Path(directory)
            source = base_path / "raw_academico" / "FMEA.pdf"
            source.parent.mkdir()
            source.write_bytes(b"fake")
            output = base_path / "knowledge" / "manutencao" / "fmea.md"
            output.parent.mkdir(parents=True)
            output.write_text("> Fonte original: raw_academico/FMEA.pdf  \nconteúdo existente", encoding="utf-8")
            with patch("apps.livia_assistant.rag.pdf_extractor.extract_pdf_text") as extract:
                result = convert_pdf_to_markdown(source, base_path / "knowledge")
        extract.assert_not_called()
        self.assertEqual(result["status"], "ignored")
        self.assertIn("already exists", result["reason"])


class ConvertSelectedPDFsCommandTests(SimpleTestCase):
    def test_command_does_not_break_without_raw_directory(self):
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            output = StringIO()
            call_command("convert_livia_selected_pdfs", stdout=output)
        self.assertIn("Pasta não encontrada", output.getvalue())

    def test_command_ignores_large_pdf_and_converts_selected_small_pdf(self):
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            base_path = Path(directory)
            raw_path = base_path / "knowledge" / "raw_academico"
            raw_path.mkdir(parents=True)
            (raw_path / "FMEA falhas.pdf").write_bytes(b"fake")
            large = raw_path / "TPM manutencao.pdf"
            with large.open("wb") as file_handle:
                file_handle.truncate(21 * 1024 * 1024)
            output = StringIO()

            with patch("apps.livia_assistant.rag.pdf_extractor.extract_pdf_text", return_value=LONG_TEXT):
                call_command("convert_livia_selected_pdfs", stdout=output)

            generated = list((base_path / "knowledge" / "manutencao").glob("*.md"))

        self.assertEqual(len(generated), 1)
        self.assertIn("PDFs candidatos avaliados: 1", output.getvalue())
        self.assertIn("PDFs grandes ignorados: 1", output.getvalue())
