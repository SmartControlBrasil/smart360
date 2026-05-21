from unittest.mock import patch

from django.test import TestCase

from apps.livia_assistant.models import LiviaConversation, LiviaKnowledgeItem, LiviaLeadCapture, LiviaMessage
from apps.livia_assistant.services import LiviaAssistantService


class RecordingClient:
    def __init__(self):
        self.messages = None
        self.context = None

    def generate_reply(self, *, system_prompt, messages, context=None):
        self.messages = messages
        self.context = context
        return "Resposta registrada pela Lívia."


class LiviaAssistantServiceTests(TestCase):
    def setUp(self):
        self.service = LiviaAssistantService()

    def test_get_or_create_conversation_creates_open_conversation(self):
        conversation = self.service.get_or_create_conversation(session_key="abc123", source_page="/")

        self.assertEqual(conversation.session_key, "abc123")
        self.assertEqual(conversation.source_page, "/")
        self.assertEqual(conversation.status, LiviaConversation.Status.OPEN)

    def test_register_user_message(self):
        conversation = self.service.get_or_create_conversation(session_key="abc123")

        message = self.service.register_user_message(conversation, "Preciso de manutenção")

        self.assertEqual(message.role, LiviaMessage.Role.USER)
        self.assertEqual(message.content, "Preciso de manutenção")

    def test_detects_lead_intent(self):
        lead_phrases = [
            "quero orçamento",
            "preciso de manutenção",
            "me chama no whatsapp",
        ]

        for phrase in lead_phrases:
            with self.subTest(phrase=phrase):
                self.assertTrue(self.service.detect_lead_intent(phrase))

    def test_generate_response_saves_assistant_message(self):
        conversation = self.service.get_or_create_conversation(session_key="response-session")
        self.service.register_user_message(conversation, "Olá")

        response = self.service.generate_response(conversation, "Olá")

        self.assertEqual(response.reply[:5], "Olá, ")
        self.assertEqual(conversation.messages.filter(role=LiviaMessage.Role.ASSISTANT).count(), 1)

    def test_generate_response_uses_knowledge_context(self):
        conversation = self.service.get_or_create_conversation(session_key="knowledge-session")
        self.service.register_user_message(conversation, "Quero saber sobre PMOC")
        LiviaKnowledgeItem.objects.create(
            title="PMOC",
            slug="pmoc-teste",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="PMOC organiza manutenção, operação e controle de sistemas de climatização.",
            keywords="pmoc climatização",
            priority=10,
        )
        client = RecordingClient()

        with patch("apps.livia_assistant.services.get_livia_ai_client", return_value=client):
            self.service.generate_response(conversation, "Quero saber sobre PMOC")

        self.assertIn("PMOC", client.context["knowledge_context"])
        self.assertTrue(conversation.messages.filter(metadata__knowledge_context_used=True).exists())

    def test_generate_response_uses_recent_history(self):
        conversation = self.service.get_or_create_conversation(session_key="history-session")
        self.service.register_user_message(conversation, "Preciso de manutenção")
        self.service.register_assistant_message(conversation, "Claro, em qual equipamento?")
        self.service.register_user_message(conversation, "É uma câmara climática")
        client = RecordingClient()

        with patch("apps.livia_assistant.services.get_livia_ai_client", return_value=client):
            self.service.generate_response(conversation, "É uma câmara climática")

        self.assertEqual([message["role"] for message in client.messages[:3]], ["user", "assistant", "user"])
        self.assertIn("câmara climática", client.messages[-1]["content"])

    def test_create_or_update_lead_capture(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-session")
        extracted_data = {
            "name": "Marcelo",
            "email": "marcelo@example.com",
            "phone": "11999999999",
            "company": "Smart Test",
            "city": "São Paulo",
            "service_interest": "manutenção industrial",
            "urgency": LiviaLeadCapture.Urgency.HIGH,
            "notes": "quero orçamento de manutenção",
        }

        lead = self.service.create_or_update_lead_capture(conversation, extracted_data)
        conversation.refresh_from_db()

        self.assertTrue(lead.is_qualified)
        self.assertEqual(conversation.status, LiviaConversation.Status.QUALIFIED)
        self.assertEqual(conversation.visitor_name, "Marcelo")
