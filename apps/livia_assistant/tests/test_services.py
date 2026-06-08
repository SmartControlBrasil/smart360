from unittest.mock import patch

from django.test import override_settings, TestCase

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

        self.assertIn("lívia", response.reply.lower())
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

    def test_response_for_liro_contains_educational_context(self):
        conversation = self.service.get_or_create_conversation(session_key="liro-session")
        self.service.register_user_message(conversation, "Quero saber do LIRO")
        LiviaKnowledgeItem.objects.create(
            title="LIRO / LittleBot",
            slug="liro-littlebot-test",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="O LIRO é um robô educacional inteligente para escolas e ambientes de aprendizagem.",
            keywords="liro littlebot robô educacional",
            priority=20,
        )

        response = self.service.generate_response(conversation, "Quero saber do LIRO")
        self.assertTrue(
            "robô educacional" in response.reply.lower() or "littlebot" in response.reply.lower()
        )

    def test_response_for_orbit_contains_security_context(self):
        conversation = self.service.get_or_create_conversation(session_key="orbit-session")
        self.service.register_user_message(conversation, "O Orbit serve para patrulhamento?")
        LiviaKnowledgeItem.objects.create(
            title="Orbit Bot / Patrol Bot",
            slug="orbit-patrol-test",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="Robô de patrulhamento e segurança para grandes áreas.",
            keywords="orbit patrol patrulhamento segurança",
            priority=20,
        )

        response = self.service.generate_response(conversation, "O Orbit serve para patrulhamento?")
        self.assertTrue(
            "patrulhamento" in response.reply.lower() or "segurança" in response.reply.lower()
        )

    def test_response_for_neo_contains_reception_or_service(self):
        conversation = self.service.get_or_create_conversation(session_key="neo-session")
        self.service.register_user_message(conversation, "Fale sobre o Neo Bot")
        LiviaKnowledgeItem.objects.create(
            title="Neo Bot",
            slug="neo-bot-test",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="Robô de recepção e atendimento para empresas e eventos.",
            keywords="neo bot recepção atendimento",
            priority=20,
        )

        response = self.service.generate_response(conversation, "Fale sobre o Neo Bot")
        self.assertTrue(
            "recepção" in response.reply.lower() or "atendimento" in response.reply.lower()
        )

    def test_response_for_mitsubishi_clp_mentions_melsec_or_clp(self):
        conversation = self.service.get_or_create_conversation(session_key="melsec-session")
        self.service.register_user_message(conversation, "Vocês trabalham com CLP Mitsubishi?")
        LiviaKnowledgeItem.objects.create(
            title="CLPs Mitsubishi / MELSEC",
            slug="melsec-test",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="Os CLPs Mitsubishi da linha MELSEC são aplicados em controle de máquinas e processos.",
            keywords="clp mitsubishi melsec plc",
            priority=20,
        )

        response = self.service.generate_response(conversation, "Vocês trabalham com CLP Mitsubishi?")
        self.assertTrue(
            "melsec" in response.reply.lower() or "clp" in response.reply.lower()
        )

    def test_response_for_mitsubishi_motors_disambiguates_scope(self):
        conversation = self.service.get_or_create_conversation(session_key="motors-session")
        self.service.register_user_message(conversation, "Vocês vendem carro da Mitsubishi Motors?")

        response = self.service.generate_response(conversation, "Vocês vendem carro da Mitsubishi Motors?")

        self.assertIn("mitsubishi electric", response.reply.lower())
        self.assertIn("automação industrial", response.reply.lower())

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_real_case_cao_robo_returns_buddy_not_pmoc(self):
        conversation = self.service.get_or_create_conversation(session_key="case-cao-robo")
        self.service.register_user_message(conversation, "quero saber sobre o cão robo")
        LiviaKnowledgeItem.objects.create(
            title="Buddy Bot",
            slug="case-buddy",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="O Buddy Bot é um robô quadrúpede para inspeção e segurança patrimonial.",
            keywords="buddy budy cao robo cachorro robo quadrupede",
            priority=80,
        )
        LiviaKnowledgeItem.objects.create(
            title="PMOC",
            slug="case-pmoc",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="PMOC em climatização.",
            keywords="pmoc",
            priority=95,
        )

        response = self.service.generate_response(conversation, "quero saber sobre o cão robo")
        lowered = response.reply.lower()
        self.assertTrue("buddy bot" in lowered or "quadrupede" in lowered)
        self.assertNotIn("pmoc", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_real_case_budy_returns_buddy_not_generic_fallback(self):
        conversation = self.service.get_or_create_conversation(session_key="case-budy")
        self.service.register_user_message(conversation, "o budy")
        LiviaKnowledgeItem.objects.create(
            title="Buddy Bot",
            slug="case-buddy-budy",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="O Buddy Bot é um robô quadrúpede para inspeção e segurança patrimonial.",
            keywords="buddy budy cao robo cachorro robo quadrupede",
            priority=80,
        )

        response = self.service.generate_response(conversation, "o budy")
        lowered = response.reply.lower()
        self.assertIn("buddy bot", lowered)
        self.assertNotIn("sou a lívia, assistente virtual", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_real_case_cao_robo_pronta_entrega_mentions_confirmation(self):
        conversation = self.service.get_or_create_conversation(session_key="case-pronta-entrega")
        self.service.register_user_message(conversation, "o cão robo, tem a pronta entrega?")
        LiviaKnowledgeItem.objects.create(
            title="Buddy Bot",
            slug="case-buddy-stock",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="O Buddy Bot é um robô quadrúpede para inspeção e segurança patrimonial.",
            keywords="buddy budy cao robo cachorro robo quadrupede pronta entrega",
            priority=80,
        )

        response = self.service.generate_response(conversation, "o cão robo, tem a pronta entrega?")
        lowered = response.reply.lower()
        self.assertIn("buddy bot", lowered)
        self.assertTrue("pronta entrega" in lowered or "disponibilidade" in lowered)
        self.assertIn("confirm", lowered)
        self.assertNotIn("temos em estoque", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_real_case_neo_bot_returns_reception_content(self):
        conversation = self.service.get_or_create_conversation(session_key="case-neo")
        self.service.register_user_message(conversation, "fale sobre o Neo bot")
        LiviaKnowledgeItem.objects.create(
            title="Neo Bot",
            slug="case-neo-bot",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="O Neo Bot é um robô de recepção e atendimento.",
            keywords="neo neo bot neobot robo de recepcao atendimento",
            priority=80,
        )

        response = self.service.generate_response(conversation, "fale sobre o Neo bot")
        lowered = response.reply.lower()
        self.assertIn("neo bot", lowered)
        self.assertTrue("recepção" in lowered or "atendimento" in lowered)
        self.assertNotIn("sou a lívia, assistente virtual", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_real_case_robo_limpeza_returns_hygibot_not_pmoc(self):
        conversation = self.service.get_or_create_conversation(session_key="case-cleaning")
        self.service.register_user_message(conversation, "robô de limpeza")
        LiviaKnowledgeItem.objects.create(
            title="HygiBot / Dune Bot",
            slug="case-hygibot",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="Robô de limpeza autônoma para grandes áreas.",
            keywords="hygibot dune duno robo de limpeza",
            priority=80,
        )
        LiviaKnowledgeItem.objects.create(
            title="PMOC",
            slug="case-pmoc-cleaning",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="PMOC em climatização.",
            keywords="pmoc",
            priority=95,
        )

        response = self.service.generate_response(conversation, "robô de limpeza")
        lowered = response.reply.lower()
        self.assertTrue("hygibot" in lowered or "dune" in lowered or "duno" in lowered)
        self.assertNotIn("pmoc", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_pmoc_query_still_returns_pmoc(self):
        conversation = self.service.get_or_create_conversation(session_key="case-pmoc-preserved")
        self.service.register_user_message(conversation, "PMOC")
        LiviaKnowledgeItem.objects.create(
            title="PMOC",
            slug="case-pmoc-preserved-item",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="PMOC organiza manutenção, operação e controle.",
            keywords="pmoc",
            priority=95,
        )

        response = self.service.generate_response(conversation, "PMOC")
        self.assertIn("pmoc", response.reply.lower())

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_oi_can_return_fallback(self):
        conversation = self.service.get_or_create_conversation(session_key="case-oi")
        self.service.register_user_message(conversation, "oi")
        response = self.service.generate_response(conversation, "oi")
        self.assertIn("sou a lívia", response.reply.lower())
