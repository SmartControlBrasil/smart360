from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.livia_assistant.management.commands.import_livia_xyron_docs import chunk_text
from apps.livia_assistant.models import LiviaKnowledgeItem


class LiviaImportXyronDocsCommandTests(TestCase):
    def test_chunk_text_splits_large_content(self):
        text = ("Conteúdo técnico Xyron sobre robótica e integração. " * 300).strip()
        chunks = chunk_text(text, chunk_size=1200, min_chunk_size=300)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.strip() for chunk in chunks))
        self.assertTrue(all(len(chunk) <= 1300 for chunk in chunks))

    @override_settings(LIVIA_ASSISTANT_ENABLED=True)
    def test_import_is_idempotent_for_same_source(self):
        with TemporaryDirectory() as directory:
            docs_path = Path(directory)
            file_path = docs_path / "NeoBot Technical Deck.pdf"
            file_path.write_bytes(b"fake-pdf")

            extracted_text = "Linha NeoBot com aplicações em recepção, atendimento e operação. " * 140
            with patch(
                "apps.livia_assistant.management.commands.import_livia_xyron_docs.extract_pdf_text",
                return_value=extracted_text,
            ):
                call_command("import_livia_xyron_docs", path=str(docs_path), stdout=StringIO())
                first_count = LiviaKnowledgeItem.objects.filter(slug__startswith="xyron-doc-").count()

                call_command("import_livia_xyron_docs", path=str(docs_path), stdout=StringIO())
                second_count = LiviaKnowledgeItem.objects.filter(slug__startswith="xyron-doc-").count()

        self.assertGreater(first_count, 0)
        self.assertEqual(first_count, second_count)

    @override_settings(LIVIA_ASSISTANT_ENABLED=True)
    def test_import_simulated_pdf_creates_knowledge_items(self):
        with TemporaryDirectory() as directory:
            docs_path = Path(directory)
            file_path = docs_path / "LIRO Guia de Aplicação.pdf"
            file_path.write_bytes(b"fake-pdf")
            with patch(
                "apps.livia_assistant.management.commands.import_livia_xyron_docs.extract_pdf_text",
                return_value=("LIRO robô educacional para escolas e clínicas. " * 120),
            ):
                output = StringIO()
                call_command("import_livia_xyron_docs", path=str(docs_path), stdout=output)

        items = LiviaKnowledgeItem.objects.filter(slug__startswith="xyron-doc-")
        self.assertTrue(items.exists())
        self.assertTrue(items.filter(is_active=True).exists())
        self.assertIn("concluído", output.getvalue())

    @override_settings(LIVIA_ASSISTANT_ENABLED=True)
    def test_missing_folder_is_safe(self):
        output = StringIO()
        call_command("import_livia_xyron_docs", path="/tmp/path/that/does/not/exist", stdout=output)
        self.assertIn("Pasta não encontrada", output.getvalue())
        self.assertEqual(LiviaKnowledgeItem.objects.count(), 0)
