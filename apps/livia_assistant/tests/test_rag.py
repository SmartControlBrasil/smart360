from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import override_settings, TestCase

from apps.livia_assistant.models import LiviaKnowledgeChunk, LiviaKnowledgeDocument
from apps.livia_assistant.rag.chunking import split_text_into_chunks
from apps.livia_assistant.rag.context_builder import build_context_for_prompt
from apps.livia_assistant.rag.importer import import_knowledge_directory, import_markdown_file
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

    def test_import_directory_ignores_internal_directories_and_imports_approved_ones(self):
        with TemporaryDirectory() as directory:
            base_path = Path(directory) / "knowledge"
            paths = {
                "reports/audit.md": False,
                "raw_academico/raw.md": False,
                ".cache/cache.md": False,
                "__internal/internal.md": False,
                "engenharia/.hidden.md": False,
                "engenharia/__temporary.md": False,
                "engenharia/~$draft.md": False,
                "engenharia/automacao.md": True,
                "academico/guia.md": True,
            }
            for relative_path in paths:
                path = base_path / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"# {path.stem}\n\nConteúdo técnico aprovado para teste.", encoding="utf-8")

            summary = import_knowledge_directory(base_path)

        self.assertEqual(summary["created"], 2)
        self.assertEqual(summary["errors"], [])
        self.assertSetEqual(
            set(LiviaKnowledgeDocument.objects.values_list("title", flat=True)),
            {"automacao", "guia"},
        )

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

    def test_maintenance_intent_prioritizes_maintenance_documents(self):
        self._create_chunk("Mapa TPM", "TPM reduz paradas com manutenção planejada e análise de falhas.", category="manutencao")
        self._create_chunk("Componentes de Rigidez Relevantes", "Engenharia estrutural e paradas para análise.", category="engenharia")
        self._create_chunk("Guia de estudos", "Guia de estudos com módulo de manutenção.", category="academico")

        results = retrieve_livia_context("Como TPM ajuda a reduzir paradas?", limit=3)

        self.assertEqual(results[0]["category"], "manutencao")
        self.assertNotIn("Guia de estudos", [result["document_title"] for result in results])
        self.assertNotIn("Componentes de Rigidez Relevantes", [result["document_title"] for result in results])

    def test_failure_analysis_and_fmea_prioritize_maintenance(self):
        self._create_chunk("FMEA Industrial", "FMEA identifica modos de falha, causas e riscos industriais.", category="manutencao")
        self._create_chunk("Confiabilidade", "Análise de falhas aplicada à manutenção industrial.", category="manutencao")
        self._create_chunk("Guia genérico", "Conteúdo para cliente industrial.", category="academico")

        failure_results = retrieve_livia_context("Como usar análise de falhas em manutenção?", limit=3)
        fmea_results = retrieve_livia_context("Como explicar FMEA para um cliente industrial?", limit=3)

        self.assertEqual(failure_results[0]["category"], "manutencao")
        self.assertTrue("FMEA" in fmea_results[0]["document_title"] or fmea_results[0]["category"] == "manutencao")

    def test_retrieval_limits_duplicate_chunks_per_document(self):
        document = LiviaKnowledgeDocument.objects.create(
            title="Manual TPM", slug="manual-tpm", source_path="/test/manual-tpm.md", content_hash="b" * 64, category="manutencao"
        )
        for index in range(5):
            LiviaKnowledgeChunk.objects.create(document=document, content=f"TPM manutenção falhas parada trecho {index}", chunk_index=index, token_estimate=20)
        self._create_chunk("FMEA", "FMEA para manutenção e falhas.", category="manutencao")
        self._create_chunk("Disponibilidade", "Disponibilidade reduz paradas de manutenção.", category="manutencao")

        results = retrieve_livia_context("TPM manutenção falhas paradas", limit=5)
        manual_count = sum(result["document_title"] == "Manual TPM" for result in results)

        self.assertLessEqual(manual_count, 2)
        self.assertGreaterEqual(len({result["document_title"] for result in results}), 3)

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
