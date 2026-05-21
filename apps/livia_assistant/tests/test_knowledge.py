from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.livia_assistant.knowledge import LiviaKnowledgeService
from apps.livia_assistant.models import LiviaKnowledgeItem


class LiviaKnowledgeServiceTests(TestCase):
    def test_seed_creates_items_without_duplicates(self):
        output = StringIO()
        call_command("seed_livia_knowledge", stdout=output)
        first_count = LiviaKnowledgeItem.objects.count()
        call_command("seed_livia_knowledge", stdout=StringIO())

        self.assertEqual(first_count, 10)
        self.assertEqual(LiviaKnowledgeItem.objects.count(), 10)
        self.assertIn("10 created", output.getvalue())

    def test_search_returns_active_item_by_keyword(self):
        item = LiviaKnowledgeItem.objects.create(
            title="PMOC Empresarial",
            slug="pmoc-empresarial",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="Plano de manutenção para climatização.",
            keywords="climatização ar condicionado",
            priority=10,
        )

        results = LiviaKnowledgeService().search("preciso organizar climatização")

        self.assertIn(item, results)

    def test_search_ignores_inactive_item(self):
        LiviaKnowledgeItem.objects.create(
            title="Item inativo",
            slug="item-inativo",
            category=LiviaKnowledgeItem.Category.FAQ,
            content="Conteúdo que não deve aparecer.",
            keywords="palavraespecial",
            is_active=False,
        )

        results = LiviaKnowledgeService().search("palavraespecial")

        self.assertEqual(results, [])

    def test_build_context_limits_size(self):
        LiviaKnowledgeItem.objects.create(
            title="Conteúdo grande",
            slug="conteudo-grande",
            category=LiviaKnowledgeItem.Category.SERVICES,
            content="manutenção " * 400,
            keywords="manutenção",
            priority=10,
        )
        service = LiviaKnowledgeService()
        service.max_context_chars = 300

        context = service.build_context("manutenção")

        self.assertLessEqual(len(context), 360)
        self.assertIn("Base de conhecimento", context)
