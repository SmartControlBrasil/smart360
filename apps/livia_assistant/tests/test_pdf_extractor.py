from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import call, patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from apps.livia_assistant.rag.pdf_extractor import (
    build_pdf_markdown,
    convert_pdf_to_markdown,
    infer_pdf_output_category,
    normalize_pdf_text,
)


LONG_TEXT = "Conteúdo técnico sobre manutenção, falhas, confiabilidade e diagnóstico industrial. " * 20


def candidate(path, category="manutencao", score=30):
    return {"relative_path": path, "recommended_category": category, "score": score}


def selection(candidates, total_pdfs=None, oversized=0):
    return {
        "candidates": candidates,
        "candidate_count": len(candidates),
        "total_pdfs": total_pdfs if total_pdfs is not None else len(candidates) + oversized,
        "oversized_count": oversized,
        "oversized": [],
    }


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

    def test_convert_rejects_corrupted_text_without_rejected_markdown(self):
        with TemporaryDirectory() as directory:
            base_path = Path(directory)
            source = base_path / "Robotica.pdf"
            source.write_bytes(b"fake")
            with patch("apps.livia_assistant.rag.pdf_extractor.extract_pdf_text", return_value="/0 /1 /2 " * 300):
                result = convert_pdf_to_markdown(source, base_path / "knowledge")
            generated = list((base_path / "knowledge").rglob("*.md")) if (base_path / "knowledge").exists() else []
        self.assertEqual(result["status"], "error")
        self.assertEqual(generated, [])

    def test_existing_markdown_is_ignored_without_force_and_overwritten_with_force(self):
        with TemporaryDirectory() as directory:
            base_path = Path(directory)
            source = base_path / "raw_academico" / "FMEA.pdf"
            source.parent.mkdir()
            source.write_bytes(b"fake")
            output = base_path / "knowledge" / "manutencao" / "fmea.md"
            output.parent.mkdir(parents=True)
            output.write_text("> Fonte original: raw_academico/FMEA.pdf  \nconteúdo antigo", encoding="utf-8")

            with patch("apps.livia_assistant.rag.pdf_extractor.extract_pdf_text", return_value=LONG_TEXT) as extract:
                ignored = convert_pdf_to_markdown(source, base_path / "knowledge")
                converted = convert_pdf_to_markdown(source, base_path / "knowledge", force=True)
                overwritten_content = output.read_text(encoding="utf-8")

        self.assertEqual(ignored["status"], "ignored")
        self.assertEqual(converted["status"], "converted")
        extract.assert_called_once()
        self.assertNotIn("conteúdo antigo", overwritten_content)


class ConvertSelectedPDFsCommandTests(SimpleTestCase):
    def test_command_does_not_break_without_raw_directory(self):
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            output = StringIO()
            call_command("convert_livia_selected_pdfs", stdout=output)
        self.assertIn("Pasta não encontrada", output.getvalue())

    def test_limit_and_offset_control_selected_batch(self):
        candidates = [candidate(f"FMEA-{index}.pdf", score=50 - index) for index in range(5)]
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            (Path(directory) / "knowledge" / "raw_academico").mkdir(parents=True)
            with patch("apps.livia_assistant.management.commands.convert_livia_selected_pdfs.select_pdf_candidates", return_value=selection(candidates)), patch("apps.livia_assistant.management.commands.convert_livia_selected_pdfs.convert_pdf_to_markdown", return_value={"status": "converted", "output_path": "/tmp/out.md", "source_path": "/tmp/in.pdf", "reason": ""}) as convert:
                call_command("convert_livia_selected_pdfs", limit=2, offset=1, stdout=StringIO())
        self.assertEqual(convert.call_count, 2)
        self.assertEqual(convert.call_args_list[0].args[0].name, "FMEA-1.pdf")
        self.assertEqual(convert.call_args_list[1].args[0].name, "FMEA-2.pdf")

    def test_category_and_include_term_filters(self):
        candidates = [candidate("FMEA processo.pdf"), candidate("TPM.pdf"), candidate("Robotica.pdf", "engenharia")]
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            (Path(directory) / "knowledge" / "raw_academico").mkdir(parents=True)
            with patch("apps.livia_assistant.management.commands.convert_livia_selected_pdfs.select_pdf_candidates", return_value=selection(candidates)), patch("apps.livia_assistant.management.commands.convert_livia_selected_pdfs.convert_pdf_to_markdown", return_value={"status": "converted", "output_path": "/tmp/out.md", "source_path": "/tmp/in.pdf", "reason": ""}) as convert:
                call_command("convert_livia_selected_pdfs", category="manutencao", include_term=["fmea"], stdout=StringIO())
        convert.assert_called_once()
        self.assertEqual(convert.call_args.args[0].name, "FMEA processo.pdf")

    def test_dry_run_does_not_generate_markdown(self):
        candidates = [candidate("FMEA.pdf")]
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            (Path(directory) / "knowledge" / "raw_academico").mkdir(parents=True)
            output = StringIO()
            with patch("apps.livia_assistant.management.commands.convert_livia_selected_pdfs.select_pdf_candidates", return_value=selection(candidates)), patch("apps.livia_assistant.management.commands.convert_livia_selected_pdfs.convert_pdf_to_markdown") as convert:
                call_command("convert_livia_selected_pdfs", dry_run=True, stdout=output)
        convert.assert_not_called()
        self.assertIn("Dry-run", output.getvalue())

    def test_force_is_forwarded_and_existing_is_reported_without_force(self):
        candidates = [candidate("FMEA.pdf")]
        ignored = {"status": "ignored", "output_path": "/tmp/fmea.md", "source_path": "/tmp/FMEA.pdf", "reason": "Markdown already exists for this source"}
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            (Path(directory) / "knowledge" / "raw_academico").mkdir(parents=True)
            with patch("apps.livia_assistant.management.commands.convert_livia_selected_pdfs.select_pdf_candidates", return_value=selection(candidates)), patch("apps.livia_assistant.management.commands.convert_livia_selected_pdfs.convert_pdf_to_markdown", return_value=ignored) as convert:
                output = StringIO()
                call_command("convert_livia_selected_pdfs", stdout=output)
                call_command("convert_livia_selected_pdfs", force=True, stdout=StringIO())
        self.assertEqual(convert.call_args_list, [call(convert.call_args_list[0].args[0], convert.call_args_list[0].args[1], force=False), call(convert.call_args_list[1].args[0], convert.call_args_list[1].args[1], force=True)])
        self.assertIn("PDFs ignorados por já existir: 1", output.getvalue())

    def test_existing_candidate_is_skipped_before_limit_unless_forced(self):
        candidates = [candidate("FMEA.pdf")]
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            base_path = Path(directory)
            raw_path = base_path / "knowledge" / "raw_academico"
            raw_path.mkdir(parents=True)
            source = raw_path / "FMEA.pdf"
            source.write_bytes(b"fake")
            output_path = base_path / "knowledge" / "manutencao" / "fmea.md"
            output_path.parent.mkdir(parents=True)
            output_path.write_text("> Fonte original: raw_academico/FMEA.pdf  \nexistente", encoding="utf-8")
            converted = {"status": "converted", "output_path": str(output_path), "source_path": str(source), "reason": ""}
            with patch("apps.livia_assistant.management.commands.convert_livia_selected_pdfs.select_pdf_candidates", return_value=selection(candidates)), patch("apps.livia_assistant.management.commands.convert_livia_selected_pdfs.convert_pdf_to_markdown", return_value=converted) as convert:
                output = StringIO()
                call_command("convert_livia_selected_pdfs", stdout=output)
                convert.assert_not_called()
                call_command("convert_livia_selected_pdfs", force=True, stdout=StringIO())
        convert.assert_called_once()
        self.assertIn("PDFs ignorados por já existir: 1", output.getvalue())

    def test_large_and_unreadable_pdfs_do_not_generate_rejected_markdown(self):
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            base_path = Path(directory)
            raw_path = base_path / "knowledge" / "raw_academico"
            raw_path.mkdir(parents=True)
            (raw_path / "FMEA falhas.pdf").write_bytes(b"fake")
            large = raw_path / "TPM manutencao.pdf"
            with large.open("wb") as file_handle:
                file_handle.truncate(21 * 1024 * 1024)
            with patch("apps.livia_assistant.rag.pdf_extractor.extract_pdf_text", return_value="/0 /1 /2 " * 300):
                call_command("convert_livia_selected_pdfs", stdout=StringIO(), stderr=StringIO())
            generated = list((base_path / "knowledge").rglob("__rejected*.md"))
        self.assertEqual(generated, [])
