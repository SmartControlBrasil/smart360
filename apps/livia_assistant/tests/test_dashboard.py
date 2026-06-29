from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.livia_assistant.models import LiviaConversation, LiviaKnowledgeItem, LiviaLeadCapture, LiviaMessage


class LiviaDashboardTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_superuser(
            email="admin-livia@example.com",
            password="testpass123",
            first_name="Admin",
        )
        self.client.force_login(self.user)
        self.conversation = LiviaConversation.objects.create(
            session_key="dash-session",
            visitor_name="Cliente Teste",
            visitor_phone="11999999999",
            source_page="/contato/",
        )
        LiviaMessage.objects.create(
            conversation=self.conversation,
            role=LiviaMessage.Role.USER,
            content="Preciso de manutenção industrial",
        )
        LiviaMessage.objects.create(
            conversation=self.conversation,
            role=LiviaMessage.Role.ASSISTANT,
            content="Posso te ajudar com o diagnóstico inicial.",
        )
        LiviaLeadCapture.objects.create(
            conversation=self.conversation,
            name="Cliente Teste",
            phone="11999999999",
            service_interest="manutenção industrial",
            is_qualified=True,
        )


    def test_livia_dashboard_loads_with_responsive_tables(self):
        response = self.client.get(reverse("admin-shell:livia-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin_shell/livia_dashboard.html")
        self.assertContains(response, "Lívia Assistente")
        self.assertContains(response, "Conversas recentes")
        self.assertContains(response, "livia-table-wrapper")
        self.assertContains(response, "livia-dashboard-conversations-table")

    def test_livia_conversation_list_loads_with_responsive_table(self):
        response = self.client.get(reverse("admin-shell:livia-conversations"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin_shell/livia_conversations.html")
        self.assertContains(response, "Conversas")
        self.assertContains(response, "Cliente Teste")
        self.assertContains(response, "livia-table-wrapper")
        self.assertContains(response, "livia-conversations-table")

    def test_dashboard_leads_responds_for_admin_user(self):
        response = self.client.get(reverse("admin-shell:livia-leads"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cliente Teste")
        self.assertContains(response, "manutenção industrial")

    def test_conversation_detail_shows_messages(self):
        response = self.client.get(reverse("admin-shell:livia-conversation-detail", args=[self.conversation.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Preciso de manutenção industrial")
        self.assertContains(response, "Posso te ajudar com o diagnóstico inicial.")

    def test_knowledge_list_responds_for_admin_user(self):
        LiviaKnowledgeItem.objects.create(
            title="PMOC",
            slug="pmoc-dashboard",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="Base para PMOC.",
            keywords="pmoc",
        )

        response = self.client.get(reverse("admin-shell:livia-knowledge"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PMOC")
