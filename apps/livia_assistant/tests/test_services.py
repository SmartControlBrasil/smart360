from unittest.mock import patch

from django.core.management import call_command
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

    def _seed_knowledge(self):
        call_command("seed_livia_knowledge")

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
            "quero proposta técnica",
            "quero agendar uma visita",
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

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_same_conversation_cleaning_intent_overrides_previous_buddy_context(self):
        conversation = self.service.get_or_create_conversation(session_key="case-context-switch")
        LiviaKnowledgeItem.objects.create(
            title="Buddy Bot",
            slug="context-buddy",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="Robô quadrúpede para inspeção e segurança patrimonial.",
            keywords="buddy budy cao robo cachorro robo quadrupede",
            priority=80,
        )
        LiviaKnowledgeItem.objects.create(
            title="HygiBot / Dune Bot",
            slug="context-hygibot",
            category=LiviaKnowledgeItem.Category.TECHNICAL,
            content="Robô de limpeza autônoma para grandes áreas.",
            keywords="hygibot hygi bot duno dune dunobot robo de limpeza limpeza",
            priority=80,
        )

        self.service.register_user_message(conversation, "quero saber sobre o cão robo")
        first = self.service.generate_response(conversation, "quero saber sobre o cão robo")
        self.assertIn("buddy bot", first.reply.lower())

        self.service.register_user_message(conversation, "robô de limpeza")
        second = self.service.generate_response(conversation, "robô de limpeza")
        lowered = second.reply.lower()
        self.assertTrue("hygibot" in lowered or "dune" in lowered or "duno" in lowered)
        self.assertNotIn("buddy bot", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_curated_prompt_neobot(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="curated-neo")
        self.service.register_user_message(conversation, "fale sobre o neobot")
        response = self.service.generate_response(conversation, "fale sobre o neobot")
        lowered = response.reply.lower()
        self.assertIn("neobot", lowered)
        self.assertTrue("recep" in lowered or "atendimento" in lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_curated_prompt_neobot_languages(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="curated-neo-lang")
        self.service.register_user_message(conversation, "quais idiomas o neo fala?")
        response = self.service.generate_response(conversation, "quais idiomas o neo fala?")
        lowered = response.reply.lower()
        self.assertTrue("idioma" in lowered or "multiling" in lowered)
        self.assertTrue("20" in lowered or "vinte" in lowered or "mais de" in lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_curated_prompt_liro_sala_aula(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="curated-liro-class")
        self.service.register_user_message(conversation, "como o liro ajuda na sala de aula?")
        response = self.service.generate_response(conversation, "como o liro ajuda na sala de aula?")
        lowered = response.reply.lower()
        self.assertTrue("pedag" in lowered or "professor" in lowered or "bncc" in lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_curated_prompt_liro_apae(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="curated-liro-apae")
        self.service.register_user_message(conversation, "liro serve para apae?")
        response = self.service.generate_response(conversation, "liro serve para apae?")
        lowered = response.reply.lower()
        self.assertTrue(
            "apae" in lowered or "inclus" in lowered or "neurodiverg" in lowered or "multidisciplinar" in lowered
        )

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_curated_prompt_liro_plano_aula_infantil(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="curated-liro-plan")
        self.service.register_user_message(conversation, "plano de aula com liro para educação infantil")
        response = self.service.generate_response(conversation, "plano de aula com liro para educação infantil")
        lowered = response.reply.lower()
        self.assertTrue("educacao infantil" in lowered or "historia" in lowered or "cores" in lowered or "sentimentos" in lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_curated_prompt_robo_limpeza_not_buddy(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="curated-cleaning")
        self.service.register_user_message(conversation, "robô de limpeza")
        response = self.service.generate_response(conversation, "robô de limpeza")
        lowered = response.reply.lower()
        self.assertTrue("hygibot" in lowered or "limpeza aut" in lowered or "varrer" in lowered or "aspirar" in lowered)
        self.assertNotIn("buddy", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_curated_prompt_hygibot_academia(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="curated-hygibot-gym")
        self.service.register_user_message(conversation, "hygibot serve para academia?")
        response = self.service.generate_response(conversation, "hygibot serve para academia?")
        lowered = response.reply.lower()
        self.assertIn("academia", lowered)
        self.assertTrue(
            "áreas internas" in lowered
            or "areas internas" in lowered
            or "grandes áreas" in lowered
            or "grandes areas" in lowered
        )

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_curated_prompt_orbit_patrol(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="curated-orbit-patrol")
        self.service.register_user_message(conversation, "orbit faz patrulha?")
        response = self.service.generate_response(conversation, "orbit faz patrulha?")
        lowered = response.reply.lower()
        self.assertTrue("patrulh" in lowered or "seguranca autonoma" in lowered or "navegacao a laser" in lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_curated_prompt_orbit_thermal(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="curated-orbit-thermal")
        self.service.register_user_message(conversation, "orbit tem câmera térmica?")
        response = self.service.generate_response(conversation, "orbit tem câmera térmica?")
        lowered = response.reply.lower()
        self.assertTrue("termica" in lowered or "temperatura" in lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_xyron_overview_question_returns_company_ecosystem(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="xyron-overview-question")
        self.service.register_user_message(conversation, "o que é a xyron?")
        response = self.service.generate_response(conversation, "o que é a xyron?")
        lowered = response.reply.lower()
        self.assertIn("xyron robotics", lowered)
        self.assertTrue("empresa" in lowered or "solu" in lowered or "ecossistema" in lowered)
        self.assertIn("liro", lowered)
        self.assertIn("hygibot", lowered)
        self.assertIn("buddy", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_xyron_single_term_returns_overview(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="xyron-overview-short")
        self.service.register_user_message(conversation, "xyron")
        response = self.service.generate_response(conversation, "xyron")
        lowered = response.reply.lower()
        self.assertIn("xyron robotics", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_alias_hygbot_returns_hygibot_not_safety(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="alias-hygbot")
        self.service.register_user_message(conversation, "hygbot")
        response = self.service.generate_response(conversation, "hygbot")
        lowered = response.reply.lower()
        self.assertTrue("hygibot" in lowered or "limpeza" in lowered)
        self.assertNotIn("risco técnico", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_alias_lttle_returns_liro_not_safety(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="alias-lttle")
        self.service.register_user_message(conversation, "lttle")
        response = self.service.generate_response(conversation, "lttle")
        lowered = response.reply.lower()
        self.assertTrue("liro" in lowered or "littlebot" in lowered)
        self.assertNotIn("risco técnico", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_unknown_product_connectbot_does_not_trigger_safety(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="unknown-connectbot")
        self.service.register_user_message(conversation, "connectbot")
        response = self.service.generate_response(conversation, "connectbot")
        lowered = response.reply.lower()
        self.assertIn("não encontrei esse modelo", lowered)
        self.assertIn("liro", lowered)
        self.assertNotIn("risco técnico", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_safety_still_triggers_for_burn_smell(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="safety-burn-smell")
        self.service.register_user_message(conversation, "cheiro de queimado no painel")
        response = self.service.generate_response(conversation, "cheiro de queimado no painel")
        lowered = response.reply.lower()
        self.assertTrue("risco" in lowered or "emerg" in lowered)
        self.assertIn("interrompa", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_maintenance_operational_question_returns_technical_path_without_false_emergency(self):
        conversation = self.service.get_or_create_conversation(session_key="maint-operational-path")
        self.service.register_user_message(conversation, "Tenho muitas paradas em uma máquina, como vocês podem ajudar?")
        response = self.service.generate_response(conversation, "Tenho muitas paradas em uma máquina, como vocês podem ajudar?")
        lowered = response.reply.lower()
        self.assertNotIn("risco elétrico", lowered)
        self.assertNotIn("vazamento de gás", lowered)
        self.assertNotIn("cheiro de queimado", lowered)
        self.assertTrue(
            any(term in lowered for term in ("diagnóstico", "falhas", "disponibilidade", "manutenção", "fmea", "tpm"))
        )
        self.assertIn("?", response.reply)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_fmea_concept_question_answers_directly_without_premature_lead_capture(self):
        conversation = self.service.get_or_create_conversation(session_key="fmea-concept")
        self.service.register_user_message(conversation, "O que é FMEA e por que isso ajuda na manutenção?")
        response = self.service.generate_response(conversation, "O que é FMEA e por que isso ajuda na manutenção?")
        lowered = response.reply.lower()
        self.assertIn("fmea", lowered)
        self.assertTrue("falha" in lowered or "modo de falha" in lowered)
        self.assertNotIn("nome, empresa, cidade, telefone e e-mail", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_tpm_question_answers_without_emergency(self):
        conversation = self.service.get_or_create_conversation(session_key="tpm-concept")
        self.service.register_user_message(conversation, "Como TPM pode reduzir parada de máquina?")
        response = self.service.generate_response(conversation, "Como TPM pode reduzir parada de máquina?")
        lowered = response.reply.lower()
        self.assertIn("tpm", lowered)
        self.assertTrue(
            "manutenção autônoma" in lowered
            or "manutenção planejada" in lowered
            or "disponibilidade" in lowered
            or "falhas" in lowered
        )
        self.assertNotIn("risco técnico", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_recurring_failures_question_does_not_use_internal_context_placeholder(self):
        conversation = self.service.get_or_create_conversation(session_key="recurring-failures")
        self.service.register_user_message(conversation, "Minha fábrica quer reduzir falhas recorrentes, por onde começo?")
        response = self.service.generate_response(conversation, "Minha fábrica quer reduzir falhas recorrentes, por onde começo?")
        lowered = response.reply.lower()
        self.assertNotIn("há contexto interno disponível", lowered)
        self.assertTrue(
            "histórico de falhas" in lowered
            or "criticidade" in lowered
            or "diagnóstico" in lowered
            or "análise de falhas" in lowered
        )

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_real_emergency_only_with_explicit_terms(self):
        conversation = self.service.get_or_create_conversation(session_key="real-emergency-explicit")
        text = "Está saindo fumaça e cheiro de queimado do painel"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertTrue("interrompa" in lowered or "pare" in lowered)
        self.assertTrue("risco" in lowered or "emerg" in lowered)
        self.assertTrue("atendimento humano" in lowered or "equipe técnica" in lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_budget_intent_can_collect_contact_data_after_brief_explanation(self):
        conversation = self.service.get_or_create_conversation(session_key="budget-fmea-intent")
        text = "Quero orçamento para aplicar FMEA na minha fábrica"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("orçamento", lowered)
        self.assertIn("fmea", lowered)
        self.assertTrue("nome" in lowered and "empresa" in lowered and "telefone" in lowered and "e-mail" in lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_mtbf_question_has_direct_practical_explanation(self):
        conversation = self.service.get_or_create_conversation(session_key="mtbf-direct")
        text = "o que é mtbf?"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("mtbf", lowered)
        self.assertIn("mean time between failures", lowered)
        self.assertIn("tempo médio entre falhas", lowered)
        self.assertIn("confiabilidade", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_mttr_question_has_direct_practical_explanation(self):
        conversation = self.service.get_or_create_conversation(session_key="mttr-direct")
        text = "mttr"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("mttr", lowered)
        self.assertIn("mean time to repair", lowered)
        self.assertIn("tempo médio para reparo", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_mtbf_vs_mttr_difference_is_explained(self):
        conversation = self.service.get_or_create_conversation(session_key="mtbf-mttr-diff")
        text = "diferença entre mtbf e mttr"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("mtbf", lowered)
        self.assertIn("mttr", lowered)
        self.assertIn("mtbf alto", lowered)
        self.assertIn("mttr baixo", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_followup_na_linha_toda_keeps_fmea_context(self):
        conversation = self.service.get_or_create_conversation(session_key="fmea-line-followup")
        self.service.register_user_message(conversation, "fmea")
        first = self.service.generate_response(conversation, "fmea")
        self.assertIn("máquina específica", first.reply.lower())
        self.assertIn("linha inteira", first.reply.lower())

        self.service.register_user_message(conversation, "na linha toda")
        second = self.service.generate_response(conversation, "na linha toda")
        lowered = second.reply.lower()
        self.assertIn("aplicar fmea em uma linha inteira", lowered)
        self.assertIn("dividir a linha por etapas", lowered)
        self.assertIn("3 paradas mais frequentes", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_commercial_intent_quero_um_diagnostico_requests_lead_data(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-intent-diagnostico")
        text = "quero um diagnóstico"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("encaminhar para um especialista", lowered)
        self.assertIn("nome", lowered)
        self.assertIn("empresa", lowered)
        self.assertIn("cidade", lowered)
        self.assertIn("telefone/whatsapp", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_commercial_intent_quanto_custa_requests_lead_data(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-intent-quanto-custa")
        text = "quanto custa"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("especialista", lowered)
        self.assertIn("telefone/whatsapp", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_commercial_intent_preciso_de_manutencao_requests_lead_data(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-intent-manutencao")
        text = "preciso de manutenção"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("especialista", lowered)
        self.assertIn("nome", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_commercial_intent_maquina_parada_requests_lead_data(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-intent-maquina-parada")
        text = "minha máquina está parada"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("especialista", lowered)
        self.assertIn("descrição do problema", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_lead_collection_after_user_informs_name_and_phone_requests_only_missing_fields(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-intent-partial-data")
        first_text = "quero um diagnóstico"
        self.service.register_user_message(conversation, first_text)
        self.service.generate_response(conversation, first_text)

        second_text = "meu nome é Carlos e meu telefone é 1199887766"
        self.service.register_user_message(conversation, second_text)
        second_response = self.service.generate_response(conversation, second_text)
        lowered = second_response.reply.lower()
        self.assertIn("empresa", lowered)
        self.assertIn("cidade", lowered)
        self.assertIn("descrição", lowered)
        self.assertNotIn("nome", lowered)
        self.assertNotIn("telefone/whatsapp", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_comma_separated_contact_message_extracts_city_itapevi(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-intent-city-comma")
        first_text = "quero um diagnóstico"
        self.service.register_user_message(conversation, first_text)
        self.service.generate_response(conversation, first_text)

        second_text = "meu nome é Marcelo, sou da Smart Control, Itapevi, telefone 11999999999"
        self.service.register_user_message(conversation, second_text)
        response = self.service.generate_response(conversation, second_text)
        lowered = response.reply.lower()
        self.assertNotIn("cidade", lowered)
        self.assertIn("e-mail", lowered)
        self.assertIn("descrição", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_locality_question_atendem_em_manaus_receives_consultive_answer(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-locality-manaus")
        text = "vocês atendem em Manaus?"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("atendemos projetos sob avaliação", lowered)
        self.assertIn("manaus", lowered)
        self.assertIn("visita técnica", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_locality_plus_visit_campinas_has_contextual_answer(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-locality-campinas")
        text = "estou em campinas, podem vir aqui?"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("atendemos projetos sob avaliação", lowered)
        self.assertIn("campinas", lowered)
        self.assertIn("visita técnica", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_visit_request_gets_specific_visit_message(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-visit-message")
        text = "podem enviar um técnico para um diagnóstico?"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("podemos avaliar uma visita técnica", lowered)
        self.assertIn("antes de agendar", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_when_only_email_missing_asks_only_email(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-only-email-missing")
        first = "quero um diagnóstico"
        self.service.register_user_message(conversation, first)
        self.service.generate_response(conversation, first)

        second = "meu nome é Maria, sou da Empresa Alfa, cidade Campinas, telefone 11999999999, problema parada recorrente na linha"
        self.service.register_user_message(conversation, second)
        response = self.service.generate_response(conversation, second)
        lowered = response.reply.lower()
        self.assertIn("falta só o e-mail", lowered)
        self.assertNotIn("descrição", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_when_only_email_and_description_missing_requests_exactly_both(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-email-description-missing")
        first = "quero um diagnóstico"
        self.service.register_user_message(conversation, first)
        self.service.generate_response(conversation, first)

        second = "meu nome é Joao, sou da Empresa Beta, cidade Manaus, telefone 11999999999"
        self.service.register_user_message(conversation, second)
        response = self.service.generate_response(conversation, second)
        lowered = response.reply.lower()
        self.assertIn("falta só seu e-mail", lowered)
        self.assertIn("breve descrição", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_buddy_remains_buddy(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="alias-buddy")
        self.service.register_user_message(conversation, "buddy")
        response = self.service.generate_response(conversation, "buddy")
        lowered = response.reply.lower()
        self.assertIn("buddy bot", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_neo_bot_remains_neo(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="alias-neo-bot")
        self.service.register_user_message(conversation, "neo bot")
        response = self.service.generate_response(conversation, "neo bot")
        lowered = response.reply.lower()
        self.assertIn("neobot", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_dune_remains_hygibot(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="alias-dune")
        self.service.register_user_message(conversation, "dune")
        response = self.service.generate_response(conversation, "dune")
        lowered = response.reply.lower()
        self.assertTrue("hygibot" in lowered or "duno" in lowered or "dune" in lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_nebot_typo_returns_neobot_not_hostbot(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="nebot-height")
        self.service.register_user_message(conversation, "qual é a altura do nebot")
        response = self.service.generate_response(conversation, "qual é a altura do nebot")
        lowered = response.reply.lower()
        self.assertTrue("neobot" in lowered or "100 cm" in lowered or "45 x 100 x 40" in lowered)
        self.assertNotIn("hostbot", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_neobot_context_battery_duration(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="neo-context-battery")
        self.service.register_user_message(conversation, "fale sobre o NeoBot")
        self.service.generate_response(conversation, "fale sobre o NeoBot")
        self.service.register_user_message(conversation, "quanto tempo dura a bateria?")
        response = self.service.generate_response(conversation, "quanto tempo dura a bateria?")
        lowered = response.reply.lower()
        self.assertTrue("10 horas" in lowered or "autonomia" in lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_neobot_context_recharge_time(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="neo-context-recharge")
        self.service.register_user_message(conversation, "fale sobre o NeoBot")
        self.service.generate_response(conversation, "fale sobre o NeoBot")
        self.service.register_user_message(conversation, "a recarga é feita em quanto tempo?")
        response = self.service.generate_response(conversation, "a recarga é feita em quanto tempo?")
        lowered = response.reply.lower()
        self.assertTrue("9 horas" in lowered or "aproximadamente 9" in lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_neobot_context_battery_reserve_not_invented(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="neo-context-reserve")
        self.service.register_user_message(conversation, "fale sobre o NeoBot")
        self.service.generate_response(conversation, "fale sobre o NeoBot")
        self.service.register_user_message(conversation, "tem bateria reserva?")
        response = self.service.generate_response(conversation, "tem bateria reserva?")
        lowered = response.reply.lower()
        self.assertIn("na base atual", lowered)
        self.assertIn("não tenho confirmação", lowered)
        self.assertIn("validar com a equipe", lowered)
        self.assertNotIn("tem bateria reserva", lowered.replace("não", ""))
