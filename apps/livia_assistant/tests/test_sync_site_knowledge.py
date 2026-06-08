from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.livia_assistant.models import LiviaKnowledgeItem
from apps.livia_assistant.services import LiviaAssistantService


class LiviaSiteKnowledgeSyncCommandTests(TestCase):
    @override_settings(LIVIA_ASSISTANT_ENABLED=True)
    def test_sync_creates_or_updates_xyron_item(self):
        out = StringIO()
        call_command("sync_livia_site_knowledge", stdout=out)

        self.assertTrue(
            LiviaKnowledgeItem.objects.filter(slug="site-smart-control-xyron-robotics", is_active=True).exists()
        )
        self.assertIn("sync_livia_site_knowledge completed", out.getvalue())

    @override_settings(LIVIA_ASSISTANT_ENABLED=True)
    def test_sync_is_idempotent_no_duplicates(self):
        call_command("sync_livia_site_knowledge")
        first_count = LiviaKnowledgeItem.objects.filter(slug__startswith="site-smart-control-").count()
        call_command("sync_livia_site_knowledge")
        second_count = LiviaKnowledgeItem.objects.filter(slug__startswith="site-smart-control-").count()

        self.assertEqual(first_count, second_count)

    @override_settings(LIVIA_ASSISTANT_ENABLED=True)
    def test_synced_content_is_clean_without_script_style(self):
        call_command("sync_livia_site_knowledge")
        item = LiviaKnowledgeItem.objects.filter(slug="site-smart-control-xyron-robotics").first()
        self.assertIsNotNone(item)
        lowered = item.content.lower()
        self.assertNotIn("<script", lowered)
        self.assertNotIn("<style", lowered)
        self.assertTrue(len(item.content) > 120)

    @override_settings(LIVIA_AI_PROVIDER="fallback", LIVIA_ASSISTANT_ENABLED=True)
    def test_specific_product_matches_remain_after_sync(self):
        call_command("seed_livia_knowledge")
        call_command("sync_livia_site_knowledge")

        service = LiviaAssistantService()
        conversation = service.get_or_create_conversation(session_key="sync-ranking-preserved")

        service.register_user_message(conversation, "neo bot")
        neo = service.generate_response(conversation, "neo bot").reply.lower()
        self.assertIn("neobot", neo)

        service.register_user_message(conversation, "robô de limpeza")
        cleaning = service.generate_response(conversation, "robô de limpeza").reply.lower()
        self.assertTrue("hygibot" in cleaning or "dune" in cleaning or "duno" in cleaning)
        self.assertNotIn("buddy", cleaning)

        service.register_user_message(conversation, "buddy")
        buddy = service.generate_response(conversation, "buddy").reply.lower()
        self.assertIn("buddy bot", buddy)

        service.register_user_message(conversation, "PMOC")
        pmoc = service.generate_response(conversation, "PMOC").reply.lower()
        self.assertIn("pmoc", pmoc)
