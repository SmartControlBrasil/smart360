import sys
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from apps.livia_assistant.rag.text_extractor import (
    convert_raw_file_to_markdown,
    extract_docx,
    extract_txt,
    infer_output_category_from_path,
    normalize_extracted_text,
)


LONG_TEXT = "Este material técnico explica conceitos práticos de automação, manutenção e confiabilidade industrial. " * 5


def fake_docx_module(text=LONG_TEXT):
    paragraph = SimpleNamespace(text=text, style=SimpleNamespace(name="Normal"))
    return SimpleNamespace(Document=lambda path: SimpleNamespace(paragraphs=[paragraph]))


class TextExtractorTests(SimpleTestCase):
    def test_normalize_extracted_text_cleans_spaces_and_excessive_breaks(self):
        result = normalize_extracted_text("  Título   técnico  \n\n\n  Primeiro   parágrafo.  \x00\n\n\n Segundo. ")
        self.assertEqual(result, "Título técnico\n\nPrimeiro parágrafo.\n\nSegundo.")

    def test_extract_txt_reads_utf8(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "utf8.txt"
            path.write_text("manutenção e automação", encoding="utf-8")
            self.assertEqual(extract_txt(path), "manutenção e automação")

    def test_extract_txt_falls_back_to_latin1(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "latin1.txt"
            path.write_bytes("manutenção técnica".encode("latin-1"))
            self.assertEqual(extract_txt(path), "manutenção técnica")

    def test_infer_output_categories(self):
        self.assertEqual(infer_output_category_from_path("Manutenção Produtiva Total/Mapa TPM.docx"), "manutencao")
        self.assertEqual(infer_output_category_from_path("Engenharia de Controle e Automação/atividade.txt"), "engenharia")
        self.assertEqual(infer_output_category_from_path("Inteligência artificial/material.txt"), "ia_aplicada")
        self.assertEqual(infer_output_category_from_path("outros/guia.txt"), "academico")

    def test_temporary_office_file_is_ignored(self):
        result = convert_raw_file_to_markdown("/tmp/~$mapa.docx", "/tmp/output")
        self.assertEqual(result["status"], "ignored")
        self.assertIn("temporary", result["reason"])

    def test_extract_docx_uses_python_docx_when_available(self):
        with patch.dict(sys.modules, {"docx": fake_docx_module()}):
            self.assertIn("material técnico", extract_docx("fake.docx"))

    def test_convert_raw_file_generates_markdown_header_and_content(self):
        with TemporaryDirectory() as directory:
            base_path = Path(directory)
            source = base_path / "raw_academico" / "Manutenção Produtiva Total" / "Mapa TPM.txt"
            source.parent.mkdir(parents=True)
            source.write_text(LONG_TEXT, encoding="utf-8")

            result = convert_raw_file_to_markdown(source, base_path / "knowledge")
            markdown = Path(result["output_path"]).read_text(encoding="utf-8")

        self.assertEqual(result["status"], "converted")
        self.assertIn("> Categoria: manutencao", markdown)
        self.assertIn("## Conteúdo extraído", markdown)
        self.assertIn("## Aplicação para a Smart Control Brasil", markdown)


class ConvertRawTextsCommandTests(SimpleTestCase):
    def test_command_does_not_break_without_raw_directory(self):
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            output = StringIO()
            call_command("convert_livia_raw_texts", stdout=output)
        self.assertIn("Pasta não encontrada", output.getvalue())

    def test_command_ignores_pdf_and_generates_txt_and_docx_markdown(self):
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            base_path = Path(directory)
            raw_path = base_path / "knowledge" / "raw_academico" / "Engenharia de Controle e Automação"
            raw_path.mkdir(parents=True)
            (raw_path / "notas.txt").write_text(LONG_TEXT, encoding="utf-8")
            (raw_path / "mapa.docx").write_bytes(b"fake docx")
            (raw_path / "ignorado.pdf").write_bytes(b"fake pdf")
            output = StringIO()

            with patch.dict(sys.modules, {"docx": fake_docx_module()}):
                call_command("convert_livia_raw_texts", stdout=output)

            generated = sorted((base_path / "knowledge" / "engenharia").glob("*.md"))

        self.assertEqual(len(generated), 2)
        self.assertIn("Arquivos encontrados: 2", output.getvalue())
        self.assertIn("Convertidos: 2", output.getvalue())
        self.assertNotIn("ignorado.pdf", output.getvalue())
