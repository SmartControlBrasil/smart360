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

        self.assertEqual(first_count, 32)
        self.assertEqual(LiviaKnowledgeItem.objects.count(), 32)
        self.assertIn("32 created", output.getvalue())
        self.assertTrue(LiviaKnowledgeItem.objects.filter(slug="xyron-liro-littlebot").exists())
        self.assertTrue(LiviaKnowledgeItem.objects.filter(slug="xyron-liro-apae-clinicas").exists())
        self.assertTrue(LiviaKnowledgeItem.objects.filter(slug="xyron-liro-planos-aula-pedagogico").exists())
        self.assertTrue(LiviaKnowledgeItem.objects.filter(slug="xyron-orbit-patrol-bot").exists())
        self.assertTrue(LiviaKnowledgeItem.objects.filter(slug="xyron-neo-bot").exists())
        self.assertTrue(LiviaKnowledgeItem.objects.filter(slug="xyron-waiterbot").exists())
        self.assertTrue(LiviaKnowledgeItem.objects.filter(slug="xyron-carebot").exists())
        self.assertTrue(LiviaKnowledgeItem.objects.filter(slug="xyron-hygibot-dune-bot").exists())
        self.assertTrue(LiviaKnowledgeItem.objects.filter(slug="xyron-hostbot").exists())
        self.assertTrue(LiviaKnowledgeItem.objects.filter(slug="xyron-buddy-bot").exists())
        self.assertTrue(LiviaKnowledgeItem.objects.filter(slug="xyron-mowerbot").exists())
        self.assertTrue(LiviaKnowledgeItem.objects.filter(slug="mitsubishi-clp-melsec").exists())
        self.assertTrue(LiviaKnowledgeItem.objects.filter(slug="mitsubishi-motors-vs-mitsubishi-electric").exists())

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

    def test_robot_query_prefers_buddy_over_pmoc(self):
        buddy = LiviaKnowledgeItem.objects.create(
            title="Buddy Bot",
            slug="xyron-buddy-bot",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="Robô quadrúpede para inspeção e segurança patrimonial.",
            keywords="buddy budy cao robo cachorro robo quadrupede",
            priority=80,
        )
        LiviaKnowledgeItem.objects.create(
            title="PMOC",
            slug="pmoc-robot-conflict-test",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="PMOC para climatização.",
            keywords="pmoc manutencao",
            priority=95,
        )

        results = LiviaKnowledgeService().search("quero saber sobre o cão robo")
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].slug, buddy.slug)

    def test_search_understands_budy_typo(self):
        buddy = LiviaKnowledgeItem.objects.create(
            title="Buddy Bot",
            slug="xyron-buddy-bot-typo",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="Robô quadrúpede para áreas de difícil acesso.",
            keywords="buddy budy cachorro robo",
            priority=80,
        )
        results = LiviaKnowledgeService().search("o budy")
        self.assertTrue(results)
        self.assertEqual(results[0].slug, buddy.slug)
