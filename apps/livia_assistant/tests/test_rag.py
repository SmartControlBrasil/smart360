from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import override_settings, TestCase

from apps.livia_assistant.models import LiviaKnowledgeChunk, LiviaKnowledgeDocument
from apps.livia_assistant.rag.chunking import split_text_into_chunks
from apps.livia_assistant.rag.context_builder import build_context_for_prompt
from apps.livia_assistant.rag.importer import import_markdown_file
from apps.livia_assistant.rag.retrieval import retrieve_livia_context


class LiviaRAGTests(TestCase):
    def _create_chunk(self, title, content, product="", category="robotica", application=""):
        document = LiviaKnowledgeDocument.objects.create(
            title=title,
            slug=title.lower().replace(" ", "-"),
            source_path=f"/test/{title}.md",
            content_hash="a" * 64,
            category=category,
            product=product,
            application=application,
        )
        return LiviaKnowledgeChunk.objects.create(document=document, content=content, chunk_index=0, token_estimate=20)

    def test_split_text_into_chunks_divides_long_text_with_overlap(self):
        chunks = split_text_into_chunks("Primeira frase longa. " * 30, max_chars=120, overlap_chars=20)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunks))
        self.assertTrue(all(len(chunk) <= 120 for chunk in chunks))

    def test_import_markdown_creates_document_and_chunks_without_duplicates(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "duno.md"
            path.write_text("# Duno\n\nRobô de limpeza para supermercados. " * 80, encoding="utf-8")
            first = import_markdown_file(path, product="Duno")
            chunk_count = LiviaKnowledgeChunk.objects.count()
            second = import_markdown_file(path, product="Duno")

        self.assertEqual(first["status"], "created")
        self.assertGreater(chunk_count, 0)
        self.assertEqual(second["status"], "ignored")
        self.assertEqual(LiviaKnowledgeChunk.objects.count(), chunk_count)

    def test_retrieval_finds_duno_for_supermarket_cleaning(self):
        self._create_chunk("Duno / Dunobot", "Robô de limpeza para corredores e áreas amplas de supermercados.", product="Duno")
        results = retrieve_livia_context("robô de limpeza para supermercado")
        self.assertEqual(results[0]["product"], "Duno")

    def test_retrieval_finds_reception_robots(self):
        self._create_chunk("NeoBot", "Robô recepcionista interativo para empresas e eventos.", product="NeoBot")
        self._create_chunk("HostBot", "Robô de recepção com duas telas e conversas com IA.", product="HostBot")
        results = retrieve_livia_context("robô recepcionista", limit=5)
        titles = {result["document_title"] for result in results}
        self.assertIn("NeoBot", titles)
        self.assertIn("HostBot", titles)

    def test_build_context_for_prompt_returns_formatted_context(self):
        self._create_chunk("Duno / Dunobot", "Robô de limpeza para supermercados.", product="Duno")
        context = build_context_for_prompt("limpeza de supermercado")
        self.assertIn("[DOCUMENTO: Duno / Dunobot]", context)
        self.assertIn("Produto: Duno", context)
        self.assertIn("Trecho:", context)

    def test_import_command_does_not_break_without_knowledge_directory(self):
        with TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)):
            output = StringIO()
            call_command("import_livia_rag_knowledge", stdout=output)
        self.assertIn("Documentos importados: 0", output.getvalue())
        self.assertIn("Erros encontrados: 0", output.getvalue())
