import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

from apps.livia_assistant.rag.file_audit import (
    audit_raw_knowledge_directory,
    human_readable_size,
    is_ignored_extension,
    is_supported_extension,
)


class FileAuditTests(SimpleTestCase):
    def test_human_readable_size_returns_legible_values(self):
        self.assertEqual(human_readable_size(512), "512 B")
        self.assertEqual(human_readable_size(1024), "1.00 KB")
        self.assertEqual(human_readable_size(5 * 1024 * 1024), "5.00 MB")

    def test_supported_extensions(self):
        for extension in (".txt", ".md", ".pdf", ".docx"):
            with self.subTest(extension=extension):
                self.assertTrue(is_supported_extension(extension))

    def test_ignored_extensions(self):
        for extension in (".zip", ".html", ".png", ".jpg", ".webp"):
            with self.subTest(extension=extension):
                self.assertTrue(is_ignored_extension(extension))

    def test_large_file_is_marked_and_empty_directory_is_supported(self):
        with TemporaryDirectory() as directory:
            base_path = Path(directory)
            empty_audit = audit_raw_knowledge_directory(base_path)
            self.assertEqual(empty_audit["total_files"], 0)

            large_file = base_path / "large.pdf"
            with large_file.open("wb") as file_handle:
                file_handle.truncate(21 * 1024 * 1024)
            audit = audit_raw_knowledge_directory(base_path)

        self.assertTrue(audit["files"][0]["too_large"])

    def test_audit_counts_extensions_and_does_not_extract_documents(self):
        with TemporaryDirectory() as directory:
            base_path = Path(directory)
            (base_path / "invalid.pdf").write_bytes(b"not a valid pdf")
            (base_path / "invalid.docx").write_bytes(b"not a valid docx")
            (base_path / "notes.txt").write_bytes(b"plain bytes")
            with patch.object(Path, "read_text", side_effect=AssertionError("text extraction is forbidden")):
                audit = audit_raw_knowledge_directory(base_path)

        self.assertEqual(audit["extension_counts"], {".docx": 1, ".pdf": 1, ".txt": 1})
        self.assertEqual(audit["supported_count"], 3)


    def test_hash_is_skipped_above_fifty_mb(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "huge.pdf"
            with path.open("wb") as file_handle:
                file_handle.truncate(51 * 1024 * 1024)
            with patch("apps.livia_assistant.rag.file_audit.calculate_file_hash") as calculate_hash:
                audit = audit_raw_knowledge_directory(directory)

        calculate_hash.assert_not_called()
        self.assertIsNone(audit["files"][0]["sha256"])
        self.assertEqual(audit["files"][0]["notes"], "hash skipped due to size")


class FileAuditCommandTests(SimpleTestCase):
    def test_command_does_not_break_without_raw_directory(self):
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            output = StringIO()
            call_command("audit_livia_raw_knowledge", stdout=output)
        self.assertIn("Pasta não encontrada", output.getvalue())

    def test_command_generates_markdown_and_json_reports(self):
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            base_path = Path(directory)
            raw_path = base_path / "knowledge" / "raw_academico" / "Manutenção"
            raw_path.mkdir(parents=True)
            (raw_path / "guia.txt").write_bytes(b"conteudo de teste")
            (raw_path / "pagina.html").write_bytes(b"<html>teste</html>")

            call_command("audit_livia_raw_knowledge", stdout=StringIO())

            markdown_path = base_path / "knowledge" / "reports" / "raw_academico_audit.md"
            json_path = base_path / "knowledge" / "reports" / "raw_academico_audit.json"
            report_data = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = markdown_path.read_text(encoding="utf-8")

        self.assertEqual(report_data["total_files"], 2)
        self.assertEqual(report_data["extension_counts"], {".html": 1, ".txt": 1})
        self.assertIn("## Recomendações práticas", markdown)
        self.assertIn("Não enviar knowledge/raw_academico/ para produção/VPS.", markdown)
