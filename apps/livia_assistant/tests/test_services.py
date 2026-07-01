from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.test import override_settings, TestCase

from apps.growth_engine.models import Lead
from apps.livia_assistant.lead_extractor import extract_lead_data as universal_extract_lead_data
from apps.livia_assistant.lead_state import LeadState, resolve_state
from apps.livia_assistant.models import LiviaConversation, LiviaKnowledgeItem, LiviaLeadCapture, LiviaMessage
from apps.livia_assistant.qualification import is_lead_ready_for_notification, strip_repetition_noise
from apps.livia_assistant.services import LiviaAssistantService
from apps.livia_assistant.technical_summary import (
    build_technical_service_summary,
    detect_equipment,
    detect_intent,
    detect_symptom,
    normalize_technical_corpus,
)


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

    def test_get_or_create_conversation_keeps_locked_cycle_for_new_question(self):
        conversation = self.service.get_or_create_conversation(session_key="cycle-session")
        LiviaLeadCapture.objects.create(
            conversation=conversation,
            name="Marcos",
            phone="11999999999",
            is_qualified=True,
            operational_status=LiviaLeadCapture.OperationalStatus.SENT_TO_CRM,
            crm_reference={"notification_sent_at": "2026-01-01T00:00:00Z"},
        )

        next_conversation = self.service.get_or_create_conversation(
            session_key="cycle-session",
            current_message="preciso fazer uma placa eletrônica",
        )
        self.assertEqual(conversation.id, next_conversation.id)

    def test_get_or_create_conversation_keeps_cycle_for_explicit_contact_followup_message(self):
        conversation = self.service.get_or_create_conversation(session_key="cycle-followup")
        LiviaLeadCapture.objects.create(
            conversation=conversation,
            name="Marcos",
            phone="11999999999",
            is_qualified=True,
            operational_status=LiviaLeadCapture.OperationalStatus.SENT_TO_CRM,
            crm_reference={"notification_sent_at": "2026-01-01T00:00:00Z"},
        )

        same_conversation = self.service.get_or_create_conversation(
            session_key="cycle-followup",
            current_message="meu nome é Carla e meu telefone é 11999999999",
        )
        self.assertEqual(conversation.id, same_conversation.id)

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
        client = RecordingClient()
        expected_reply = "Resposta registrada pela Lívia."

        with patch("apps.livia_assistant.services.get_livia_ai_client", return_value=client):
            response = self.service.generate_response(conversation, "Olá")

        self.assertTrue(response.reply.strip())
        self.assertEqual(response.reply, expected_reply)
        assistant_messages = conversation.messages.filter(role=LiviaMessage.Role.ASSISTANT)
        self.assertEqual(assistant_messages.count(), 1)
        assistant_message = assistant_messages.first()
        self.assertEqual(assistant_message.conversation_id, conversation.id)
        self.assertEqual(assistant_message.content, response.reply)

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
            "notes": "quero orçamento de manutenção para reduzir falhas e paradas",
        }

        lead = self.service.create_or_update_lead_capture(conversation, extracted_data)
        conversation.refresh_from_db()

        self.assertTrue(lead.is_qualified)
        self.assertEqual(conversation.status, LiviaConversation.Status.QUALIFIED)
        self.assertEqual(conversation.visitor_name, "Marcelo")

    def test_extracts_compact_commercial_data(self):
        data = self.service.extract_lead_data(
            "marcelo, smart control, 11 962196100, smartcontrol@gmail.com"
        )

        self.assertEqual(data["name"], "marcelo")
        self.assertEqual(data["company"], "smart control")
        self.assertEqual(data["phone"], "11 962196100")
        self.assertEqual(data["email"], "smartcontrol@gmail.com")
        self.assertEqual(data["city"], "")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        N8N_LIVIA_LEAD_WEBHOOK_URL="",
    )
    def test_compact_name_and_phone_does_not_qualify_without_email(self):
        mail.outbox.clear()
        conversation = self.service.get_or_create_conversation(session_key="compact-phone-lead")
        data = self.service.extract_lead_data("marcelo, smart control, 11 962196100")

        lead = self.service.create_or_update_lead_capture(conversation, data)

        self.assertFalse(lead.is_qualified)
        self.assertEqual(Lead.objects.filter(contact_name="marcelo", phone="11 962196100").count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        N8N_LIVIA_LEAD_WEBHOOK_URL="",
    )
    def test_compact_name_and_email_does_not_qualify_without_phone(self):
        mail.outbox.clear()
        conversation = self.service.get_or_create_conversation(session_key="compact-email-lead")
        data = self.service.extract_lead_data("marcelo, smart control, smartcontrol@gmail.com")

        lead = self.service.create_or_update_lead_capture(conversation, data)

        self.assertFalse(lead.is_qualified)
        self.assertEqual(Lead.objects.filter(contact_name="marcelo", email="smartcontrol@gmail.com").count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_long_intent_message_does_not_become_name_or_company(self):
        conversation = self.service.get_or_create_conversation(session_key="long-intent-not-name-company")
        data = self.service.extract_lead_data(
            "oi preciso de uma empresa de automação para cuidar dos meus equipamentos",
            conversation=conversation,
        )
        self.assertEqual(data["name"], "")
        self.assertEqual(data["company"], "")
        self.assertIn("equipamentos", data["notes"].lower())

    def test_is_lead_ready_for_notification_requires_phone_email_and_description(self):
        capture = LiviaLeadCapture(
            name="João",
            company="Arteb",
            city="São Paulo",
            phone="1156487854",
            email="joao@arteb.com.br",
            notes="preciso de automação",
        )
        self.assertTrue(is_lead_ready_for_notification(capture))
        capture.email = ""
        self.assertFalse(is_lead_ready_for_notification(capture))
        capture.email = "joao@arteb.com.br"
        capture.phone = "12345"
        self.assertFalse(is_lead_ready_for_notification(capture))

    def test_is_lead_ready_for_notification_rejects_invalid_generic_values(self):
        capture = LiviaLeadCapture(
            name="Valmir",
            company="sim gostaria",
            city="Não informada",
            phone="1145784512",
            email="nao informado",
            notes="preciso de atendimento",
        )
        self.assertFalse(is_lead_ready_for_notification(capture))

    def test_qualification_rejects_invalid_company_and_city_values(self):
        self.assertFalse(
            is_lead_ready_for_notification(
                LiviaLeadCapture(name="Valmir", company="sim gostaria", city="São Paulo", phone="1145784512", email="a@b.com")
            )
        )
        self.assertFalse(
            is_lead_ready_for_notification(
                LiviaLeadCapture(name="Valmir", company="Arteb", city="Não informado", phone="1145784512", email="a@b.com")
            )
        )
        self.assertFalse(
            is_lead_ready_for_notification(
                LiviaLeadCapture(name="Valmir", company="quero atendimento", city="São Paulo", phone="1145784512", email="a@b.com")
            )
        )
        self.assertFalse(
            is_lead_ready_for_notification(
                LiviaLeadCapture(name="Valmir", company="Arteb", city="choque térmico", phone="1145784512", email="a@b.com")
            )
        )
        self.assertFalse(
            is_lead_ready_for_notification(
                LiviaLeadCapture(name="Valmir", company="Arteb", city="", phone="1145784512", email="")
            )
        )
        self.assertFalse(
            is_lead_ready_for_notification(
                LiviaLeadCapture(
                    name="",
                    company="Eu nao falei meu nome",
                    city="Osasco",
                    phone="1145784512",
                    email="a@b.com",
                )
            )
        )
        self.assertFalse(
            is_lead_ready_for_notification(
                LiviaLeadCapture(
                    name="Valmir",
                    company="Arteb",
                    city="um ar condicionado",
                    phone="1145784512",
                    email="a@b.com",
                )
            )
        )
        self.assertFalse(
            is_lead_ready_for_notification(
                LiviaLeadCapture(
                    name="Valmir",
                    company="Arteb",
                    city="erro E2",
                    phone="1145784512",
                    email="a@b.com",
                )
            )
        )
        self.assertFalse(
            is_lead_ready_for_notification(
                LiviaLeadCapture(name="", company="", city="", phone="1145784512", email="a@b.com")
            )
        )

    def test_extract_lead_data_rejects_equipment_phrases_as_city(self):
        conversation = self.service.get_or_create_conversation(session_key="reject-equipment-city")
        extracted = self.service.extract_lead_data(
            "estou com problema em um ar condicionado",
            conversation=conversation,
        )
        self.assertEqual(extracted["city"], "")

    def test_extract_lead_data_rejects_denial_phrases_as_company(self):
        conversation = self.service.get_or_create_conversation(session_key="reject-denial-company")
        LiviaLeadCapture.objects.create(conversation=conversation, name="Teste")
        last_assistant = LiviaMessage.objects.create(
            conversation=conversation,
            role=LiviaMessage.Role.ASSISTANT,
            content="Agora preciso do nome da empresa, por favor.",
        )
        extracted = self.service.extract_lead_data(
            "Eu nao falei meu nome",
            conversation=conversation,
        )
        self.assertEqual(extracted["company"], "")

    def test_build_technical_service_summary_air_conditioner_e2(self):
        summary = build_technical_service_summary(
            raw_corpus="estou com problema em um ar condicionado erro E2",
            city="",
        )
        self.assertIn("ar-condicionado", summary.lower())
        self.assertIn("e2", summary.lower())
        self.assertNotIn("duno", summary.lower())

        summary_with_city = build_technical_service_summary(
            raw_corpus="estou com problema em um ar condicionado erro E2",
            city="Cotia",
        )
        self.assertIn("Cotia", summary_with_city)
        self.assertIn("ar-condicionado", summary_with_city.lower())
        from apps.livia_assistant.integrations import build_lead_collection_reply

        messages = [
            {"role": "assistant", "content": "Como posso te chamar?"},
            {"role": "user", "content": "meu nome é Carlos"},
            {"role": "assistant", "content": "Qual é o melhor telefone/WhatsApp para a equipe falar com você?"},
            {"role": "user", "content": "1199887766"},
        ]
        reply = build_lead_collection_reply("1199887766", messages, "").lower()
        self.assertNotIn("já tenho um contato", reply)
        self.assertNotIn("vou encaminhar", reply)
        self.assertIn("empresa", reply)

    def test_build_lead_collection_reply_rejects_sim_gostaria_as_company(self):
        from apps.livia_assistant.integrations import _collect_known_contact_fields

        messages = [
            {"role": "assistant", "content": "Em qual empresa você trabalha?"},
            {"role": "user", "content": "sim gostaria"},
        ]
        known = _collect_known_contact_fields(messages)
        self.assertEqual(known["company"], "")

    def test_build_progressive_lead_reply_never_forwards_incomplete_lead(self):
        conversation = self.service.get_or_create_conversation(session_key="progressive-incomplete-reply")
        lead = LiviaLeadCapture(
            conversation=conversation,
            name="Marcelo",
            company="Control Lab",
            phone="1178457878",
        )
        lead.save()
        reply = self.service.build_progressive_lead_reply(lead).lower()
        self.assertNotIn("vou encaminhar", reply)
        self.assertTrue("em qual cidade" in reply or "qual e-mail" in reply, msg=reply)

    def test_build_lead_confirmation_reply_only_forwards_when_notification_sent(self):
        """Teste C: linguagem de encaminhamento só com notificação enviada neste turno."""
        conversation = self.service.get_or_create_conversation(session_key="confirmation-reply-states")
        qualified_lead = LiviaLeadCapture(
            conversation=conversation,
            name="Marcelo",
            company="LogBrasil",
            city="São Paulo",
            phone="11999999999",
            email="marcelo@logbrasil.com.br",
            notes="sistema logístico web",
            is_qualified=True,
        )
        qualified_lead.save()

        sent_reply = self.service.build_lead_confirmation_reply(
            qualified_lead,
            notification_sent_this_turn=True,
        ).lower()
        self.assertIn("vou encaminhar", sent_reply)

        registered_reply = self.service.build_lead_confirmation_reply(
            qualified_lead,
            notification_sent_this_turn=False,
        ).lower()
        self.assertNotIn("vou encaminhar", registered_reply)
        self.assertNotIn("já encaminhei", registered_reply)
        self.assertIn("registrado", registered_reply)

        LiviaLeadCapture.objects.create(
            conversation=conversation,
            name="Marcelo",
            phone="11999999999",
            email="marcelo@logbrasil.com.br",
            is_qualified=True,
            operational_status=LiviaLeadCapture.OperationalStatus.SENT_TO_CRM,
            crm_reference={"notification_sent_at": "2026-01-01T00:00:00Z"},
        )
        append_reply = self.service.build_lead_confirmation_reply(
            qualified_lead,
            notification_sent_this_turn=False,
        ).lower()
        self.assertIn("acrescentar", append_reply)
        self.assertNotIn("vou encaminhar", append_reply)
        self.assertNotIn("já encaminhei", append_reply)

    def test_locked_lead_detected_after_notification_sent_at_only(self):
        conversation = self.service.get_or_create_conversation(session_key="locked-by-notification-only")
        lead = LiviaLeadCapture.objects.create(
            conversation=conversation,
            name="Marcelo",
            company="Smart Control",
            city="São Paulo",
            phone="11999999999",
            email="marcelo@smartcontrol.com.br",
            notes="sistema web com ia",
            is_qualified=True,
            crm_reference={"notification_sent_at": "2026-01-01T00:00:00Z"},
        )
        self.assertIsNotNone(self.service.get_locked_lead_capture(conversation))
        message = (
            "quero orçamento para um sistema logístico web com IA para entregas agendadas, "
            "rotas, frota e fretes em todo o Brasil"
        )
        self.assertTrue(self.service.is_new_commercial_cycle_message(message, conversation))
        self.assertTrue(self.service.detect_lead_intent(message))
        updated = self.service.create_or_update_lead_capture(
            conversation,
            self.service.extract_notes_only_lead_data(self.service.extract_lead_data(message, conversation=conversation)),
            collecting_contact=False,
            explicit_lead=lead,
        )
        reply = self.service.build_lead_confirmation_reply(updated, notification_sent_this_turn=False).lower()
        self.assertIn("acrescentar", reply)

    def test_notified_conversation_append_reply_without_reforwarding(self):
        """Teste A (serviço): conversa notificada responde acrescentar sem reenviar."""
        conversation = self.service.get_or_create_conversation(session_key="test-a-service-append")
        lead = LiviaLeadCapture.objects.create(
            conversation=conversation,
            name="Marcelo",
            company="Smart Control",
            city="São Paulo",
            phone="11999999999",
            email="marcelo@smartcontrol.com.br",
            notes="sistema web com ia",
            is_qualified=True,
            crm_reference={"notification_sent_at": "2026-01-01T00:00:00Z"},
        )
        updated = self.service.create_or_update_lead_capture(
            conversation,
            self.service.extract_notes_only_lead_data(
                self.service.extract_lead_data(
                    "quero orçamento para um sistema logístico web com entregas e rotas",
                    conversation=conversation,
                )
            ),
            collecting_contact=False,
            explicit_lead=lead,
        )
        reply = self.service.build_lead_confirmation_reply(updated, notification_sent_this_turn=False).lower()
        self.assertIn("acrescentar", reply)
        self.assertNotIn("vou encaminhar", reply)
        self.assertNotIn("já encaminhei", reply)

    def test_should_send_qualified_reply_requires_minimum_contact_and_description(self):
        conversation = self.service.get_or_create_conversation(session_key="qualified-reply-gate")
        incomplete = LiviaLeadCapture(
            conversation=conversation,
            name="Marcelo",
            company="Control Lab",
            city="Campinas",
            phone="1178457878",
        )
        complete = LiviaLeadCapture(
            conversation=conversation,
            name="Marcelo",
            company="Control Lab",
            city="Campinas",
            phone="1178457878",
            email="marcelo@controllab.com.br",
            notes="IHM apagou",
        )
        self.assertFalse(self.service.should_send_qualified_reply(incomplete))
        self.assertTrue(self.service.should_send_qualified_reply(complete))

    def test_strip_repetition_noise_from_company_value(self):
        self.assertEqual(strip_repetition_noise("buffet arroz e festa ja falei"), "buffet arroz e festa")
        self.assertEqual(strip_repetition_noise("buffet arroz e festa já falei"), "buffet arroz e festa")

    def test_create_or_update_lead_capture_sanitizes_company_with_repetition_noise(self):
        conversation = self.service.get_or_create_conversation(session_key="sanitize-company-noise")
        lead = self.service.create_or_update_lead_capture(
            conversation,
            {
                "name": "José",
                "company": "buffet arroz e festa ja falei",
                "phone": "",
                "email": "",
                "city": "",
            },
        )
        self.assertEqual(lead.company, "buffet arroz e festa")

    def test_create_or_update_lead_capture_does_not_overwrite_clean_company_with_noisy_version(self):
        conversation = self.service.get_or_create_conversation(session_key="keep-clean-company")
        self.service.create_or_update_lead_capture(
            conversation,
            {
                "name": "José",
                "company": "buffet arroz e festa",
                "phone": "",
                "email": "",
                "city": "",
            },
        )
        lead = self.service.create_or_update_lead_capture(
            conversation,
            {
                "company": "buffet arroz e festa ja falei",
            },
        )
        self.assertEqual(lead.company, "buffet arroz e festa")

    def test_extract_company_with_multiple_words_when_expected_field_is_company(self):
        conversation = self.service.get_or_create_conversation(session_key="multi-word-company")
        LiviaMessage.objects.create(
            conversation=conversation,
            role=LiviaMessage.Role.ASSISTANT,
            content="Perfeito, José. Agora preciso do nome da empresa, por favor.",
        )
        data = self.service.extract_lead_data("buffet arroz e festa", conversation=conversation)
        self.assertEqual(data["company"], "buffet arroz e festa")

    def test_create_or_update_lead_capture_persists_multi_word_company_after_name(self):
        conversation = self.service.get_or_create_conversation(session_key="company-after-name")
        self.service.create_or_update_lead_capture(
            conversation,
            {"name": "José", "company": "", "phone": "", "email": "", "city": ""},
        )
        LiviaMessage.objects.create(
            conversation=conversation,
            role=LiviaMessage.Role.ASSISTANT,
            content="Perfeito, José. Agora preciso do nome da empresa, por favor.",
        )
        self.service.register_user_message(conversation, "buffet arroz e festa")
        lead = self.service.create_or_update_lead_capture(
            conversation,
            self.service.extract_lead_data("buffet arroz e festa", conversation=conversation),
        )
        self.assertEqual(lead.name, "José")
        self.assertEqual(lead.company, "buffet arroz e festa")

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
        self.assertIn("como posso te chamar", lowered)
        self.assertNotIn("telefone/whatsapp", lowered)
        self.assertNotIn("e-mail", lowered)

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
        self.assertIn("especialista", lowered)
        self.assertIn("como posso te chamar", lowered)
        self.assertNotIn("telefone/whatsapp", lowered)
        self.assertNotIn("e-mail", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_commercial_price_question_answers_scope_without_collecting_lead_data(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-intent-quanto-custa")
        text = "quanto custa"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("valor depende", lowered)
        self.assertIn("escopo", lowered)
        self.assertFalse(response.lead_detected)
        self.assertNotIn("como posso te chamar", lowered)
        self.assertNotIn("telefone/whatsapp", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_commercial_intent_preciso_de_manutencao_requests_lead_data(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-intent-manutencao")
        text = "preciso de manutenção"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("especialista", lowered)
        self.assertIn("como posso te chamar", lowered)
        self.assertNotIn("empresa", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_open_warehouse_system_need_starts_consultative_discovery_not_contact_collection(self):
        conversation = self.service.get_or_create_conversation(session_key="warehouse-discovery-first")
        text = "preciso de um sistema para meu deposito de materiais de construção"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()

        self.assertNotIn("como posso te chamar", lowered)
        self.assertNotIn("telefone/whatsapp", lowered)
        self.assertNotIn("e-mail", lowered)
        self.assertTrue(
            any(term in lowered for term in ("estoque", "pedidos", "entregas", "planilha", "depósito", "deposito")),
            msg=response.reply,
        )

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_warehouse_discovery_starts_contact_collection_after_two_substantive_answers(self):
        conversation = self.service.get_or_create_conversation(session_key="warehouse-discovery-complete")
        opening = "preciso de um sistema para meu deposito de materiais de construção"
        self.service.register_user_message(conversation, opening)
        first = self.service.generate_response(conversation, opening)
        self.assertNotIn("como posso te chamar", first.reply.lower())

        followups = [
            "hoje a maior dor é controlar estoque e pedidos do depósito",
            "somos 8 pessoas no dia a dia e precisamos acessar pelo celular e computador",
        ]
        last_response = first
        for message in followups:
            self.service.register_user_message(conversation, message)
            last_response = self.service.generate_response(conversation, message)

        lowered = last_response.reply.lower()
        self.assertIn("como posso te chamar", lowered)
        self.assertIn("registrar seu atendimento", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_explicit_budget_for_warehouse_system_starts_contact_collection(self):
        conversation = self.service.get_or_create_conversation(session_key="warehouse-budget-intent")
        text = "quero orçamento para um sistema para meu depósito"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()

        self.assertIn("como posso te chamar", lowered)
        self.assertNotIn("telefone/whatsapp", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_commercial_intent_maquina_parada_requests_lead_data(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-intent-maquina-parada")
        text = "minha máquina está parada"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("especialista", lowered)
        self.assertIn("como posso te chamar", lowered)
        self.assertNotIn("telefone/whatsapp", lowered)
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
        self.assertNotIn("já tenho um contato", lowered)
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
        self.assertIn("qual e-mail podemos usar para formalizar o atendimento", lowered)
        self.assertNotIn("qual detalhe técnico", lowered)
        self.assertNotIn("já tenho um contato", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_isolated_lead_data_message_enters_commercial_flow(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-data-isolated")
        text = "meu nome é Marcelo, sou da Smart Control, Itapevi, telefone 11999999999"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("qual e-mail podemos usar para formalizar o atendimento", lowered)
        self.assertNotIn("qual detalhe técnico", lowered)
        self.assertNotIn("já tenho um contato", lowered)
        self.assertNotIn("sou a lívia", lowered)
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
    def test_when_contact_and_description_present_without_email_asks_email(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-only-email-missing")
        first = "quero um diagnóstico"
        self.service.register_user_message(conversation, first)
        self.service.generate_response(conversation, first)

        second = "meu nome é Maria, sou da Empresa Alfa, cidade Campinas, telefone 11999999999, problema parada recorrente na linha"
        self.service.register_user_message(conversation, second)
        response = self.service.generate_response(conversation, second)
        lowered = response.reply.lower()
        self.assertIn("qual e-mail podemos usar para formalizar o atendimento", lowered)
        self.assertNotIn("qual detalhe técnico", lowered)
        self.assertNotIn("já tenho um contato", lowered)
        self.assertNotIn("sou a lívia", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_when_minimum_contact_present_without_specific_description_continues_contextually(self):
        conversation = self.service.get_or_create_conversation(session_key="lead-email-description-missing")
        first = "quero um diagnóstico"
        self.service.register_user_message(conversation, first)
        self.service.generate_response(conversation, first)

        second = "meu nome é Joao, sou da Empresa Beta, cidade Manaus, telefone 11999999999"
        self.service.register_user_message(conversation, second)
        response = self.service.generate_response(conversation, second)
        lowered = response.reply.lower()
        self.assertIn("qual e-mail podemos usar para formalizar o atendimento", lowered)
        self.assertNotIn("qual detalhe técnico", lowered)
        self.assertNotIn("já tenho um contato", lowered)
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
    def test_xyron_school_robot_recommends_liro_without_replacing_teacher(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="xyron-school-scenario")
        text = "qual robô para escola você recomenda?"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertTrue("liro" in lowered or "littlebot" in lowered)
        self.assertIn("não substitui", lowered)
        self.assertIn("professor", lowered)
        self.assertIn("/solucoes/xyron-robotics/liro-littlebot/", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_xyron_security_robot_recommends_patrol_or_orbit_with_caution(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="xyron-security-scenario")
        text = "preciso de um robô de segurança para ronda"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertTrue("patrol" in lowered or "orbit" in lowered)
        self.assertTrue("não substitui" in lowered or "não substituem" in lowered or "sem substituir" in lowered)
        self.assertTrue("vigilante" in lowered or "equipe de segurança" in lowered)
        self.assertIn("/solucoes/xyron-robotics/orbit/", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_xyron_restaurant_robot_recommends_waiterbot_without_absolute_replacement(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="xyron-waiter-scenario")
        text = "qual robô garçom serve para restaurante?"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("waiterbot", lowered)
        self.assertTrue("sem substituir" in lowered or "sem vender a ideia de substituir" in lowered)
        self.assertIn("/solucoes/xyron-robotics/waiterbot/", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_xyron_health_robot_recommends_carebot_without_medical_promise(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="xyron-care-scenario")
        text = "qual robô para cuidado em clínica de saúde?"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("carebot", lowered)
        self.assertIn("não substitui", lowered)
        self.assertTrue("médic" in lowered or "medic" in lowered or "equipe clínica" in lowered)
        self.assertIn("/solucoes/xyron-robotics/carebot/", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_xyron_reception_events_robot_recommends_hostbot_or_neobot(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="xyron-host-scenario")
        text = "preciso de robô recepcionista para eventos"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertTrue("hostbot" in lowered or "neobot" in lowered)
        self.assertTrue("/solucoes/xyron-robotics/hostbot/" in lowered or "/solucoes/xyron-robotics/neobot/" in lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_xyron_grass_cutting_robot_recommends_mowerbot(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="xyron-mower-scenario")
        text = "qual robô para cortar grama no jardim?"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertIn("mowerbot", lowered)
        self.assertIn("/solucoes/xyron-robotics/mowerbot/", lowered)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_xyron_cleaning_robot_recommends_hygibot(self):
        self._seed_knowledge()
        conversation = self.service.get_or_create_conversation(session_key="xyron-cleaning-scenario")
        text = "qual robô de limpeza para higienização?"
        self.service.register_user_message(conversation, text)
        response = self.service.generate_response(conversation, text)
        lowered = response.reply.lower()
        self.assertTrue("hygibot" in lowered or "dune" in lowered or "duno" in lowered)
        self.assertIn("/solucoes/xyron-robotics/hygibot/", lowered)

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

    def test_lead_state_machine_transitions(self):
        snapshot = resolve_state(
            has_intent=True,
            has_name=False,
            has_company=False,
            has_city=False,
            has_phone=False,
            has_email=False,
            city_skippable=False,
            locked=False,
        )
        self.assertEqual(snapshot.state, LeadState.COLLECT_NAME)

        snapshot = resolve_state(
            has_intent=True,
            has_name=True,
            has_company=False,
            has_city=False,
            has_phone=False,
            has_email=False,
            city_skippable=False,
            locked=False,
        )
        self.assertEqual(snapshot.state, LeadState.COLLECT_COMPANY)

        snapshot = resolve_state(
            has_intent=True,
            has_name=True,
            has_company=True,
            has_city=False,
            has_phone=False,
            has_email=False,
            city_skippable=False,
            locked=False,
        )
        self.assertEqual(snapshot.state, LeadState.COLLECT_PHONE)

        snapshot = resolve_state(
            has_intent=True,
            has_name=True,
            has_company=True,
            has_city=False,
            has_phone=True,
            has_email=False,
            city_skippable=False,
            locked=False,
        )
        self.assertEqual(snapshot.state, LeadState.COLLECT_EMAIL)

        snapshot = resolve_state(
            has_intent=True,
            has_name=True,
            has_company=True,
            has_city=False,
            has_phone=True,
            has_email=True,
            city_skippable=False,
            locked=False,
        )
        self.assertEqual(snapshot.state, LeadState.COLLECT_CITY)

        snapshot = resolve_state(
            has_intent=True,
            has_name=True,
            has_company=True,
            has_city=True,
            has_phone=True,
            has_email=True,
            city_skippable=False,
            locked=False,
        )
        self.assertEqual(snapshot.state, LeadState.QUALIFIED)

    def test_universal_extractor_handles_variations(self):
        cases = [
            ("nome simples", "Marcelo", {"name": "", "company": "", "phone": "", "email": ""}),
            ("nome completo", "meu nome é Marcos Silva", {"name": "Marcos Silva"}),
            ("empresa simples", "sou da govip", {"company": "govip"}),
            ("telefone simples", "11962196100", {"phone": "11962196100"}),
            ("email simples", "marcos@govip.com", {"email": "marcos@govip.com"}),
            ("dados compactos", "marcos, govip, 11962196100, marcos@govip.com", {"phone": "11962196100", "email": "marcos@govip.com"}),
            ("sou joao empresa", "sou João da empresa XPTO", {"company": "XPTO"}),
            ("telefone rotulado", "meu telefone é 11962196100", {"phone": "11962196100"}),
            ("intenção orçamento", "quero orçamento", {"service_interest": "diagnóstico técnico"}),
            ("placa eletrônica", "preciso fazer uma placa eletrônica", {"product_hint": "engenharia_embarcada"}),
        ]

        for _, text, expected in cases:
            with self.subTest(text=text):
                extracted = universal_extract_lead_data(text)
                for key, value in expected.items():
                    self.assertEqual(getattr(extracted, key), value)


class TechnicalSummaryTests(TestCase):
    def test_normalize_technical_corpus_fixes_common_typos(self):
        corpus = normalize_technical_corpus("camara frigorifica com equipamennto e acumulo de gelo")
        self.assertIn("câmara frigorífica", corpus)
        self.assertIn("equipamento", corpus)
        self.assertNotIn("equipamennto", corpus)
        self.assertIn("acúmulo de gelo", corpus)

    def test_detect_equipment_symptom_and_intent(self):
        equipment, _ = detect_equipment("uma camara frigorifica com acumulo de gelo no ventilador")
        symptom, _ = detect_symptom("tem acumulo de gelo no ventilador")
        self.assertEqual(equipment, "câmara frigorífica")
        self.assertEqual(symptom, "acúmulo de gelo no ventilador")

        symptom, _ = detect_symptom("tem um disjuntor caindo")
        self.assertEqual(symptom, "disjuntor desarmando")

        intent = detect_intent("não tenho contrato gostaria de uma avaliação e para possivel contrato")
        self.assertIn("avaliação técnica", intent)
        self.assertIn("contrato", intent)

    def test_build_technical_service_summary_cases(self):
        summary = build_technical_service_summary(
            raw_corpus="estou com problemas em um equipamennto que parou uma camara frigorifica",
            city="Cotia",
        )
        self.assertIn("câmara frigorífica", summary)
        self.assertTrue("parada" in summary.lower())
        self.assertIn("Cotia", summary)
        self.assertNotIn("equipamennto", summary)

        summary = build_technical_service_summary(
            raw_corpus="uma camara climatica weiss nao gela sim low pressure",
            city="",
        )
        self.assertIn("câmara climática Weiss", summary)
        self.assertIn("não gela", summary)
        self.assertIn("low pressure", summary)

        summary = build_technical_service_summary(
            raw_corpus="choque termico da marca Votsch painel apagou",
            city="",
        )
        self.assertIn("choque térmico", summary)
        self.assertTrue("Vötsch" in summary or "votsch" in summary.lower())
        self.assertTrue("painel apagou" in summary.lower() or "painel apagado" in summary.lower())


class DigitalProductDiscoveryTests(TestCase):
    def test_rich_pizzaria_context_does_not_meet_minimum_discovery(self):
        from apps.livia_assistant.discovery import has_minimum_digital_product_discovery

        messages = [
            {"role": "user", "content": "voces trabalham com aplicativos moveis"},
            {"role": "user", "content": "quero um sistema de entrega de comida"},
            {
                "role": "user",
                "content": (
                    "tenho uma pequena rede de pizzarias e gostaria de ter entrega automatizada, "
                    "bem como cardapio no tablet"
                ),
            },
        ]
        self.assertFalse(has_minimum_digital_product_discovery(messages))

    def test_complete_food_delivery_context_meets_minimum_discovery(self):
        from apps.livia_assistant.discovery import has_minimum_digital_product_discovery

        messages = [
            {"role": "user", "content": "quero um sistema de entrega de comida"},
            {
                "role": "user",
                "content": (
                    "tenho uma pequena rede de pizzarias com entrega automatizada e cardapio no tablet"
                ),
            },
            {"role": "user", "content": "entregadores proprios"},
            {"role": "user", "content": "preciso de pagamento online com pix"},
            {"role": "user", "content": "sao 3 lojas na primeira fase com painel administrativo"},
        ]
        self.assertTrue(has_minimum_digital_product_discovery(messages))

    def test_digital_product_summary_uses_business_context(self):
        from apps.livia_assistant.discovery import build_digital_product_interest_summary

        summary = build_digital_product_interest_summary(
            "pequena rede de pizzarias entrega automatizada cardapio no tablet delivery de comida"
        )
        self.assertIn("pizzaria", summary.lower())
        self.assertIn("cardápio", summary.lower() or "cardapio" in summary.lower())
        self.assertNotIn("solução solicitada", summary.lower())


class LeadStateCorrectionTests(TestCase):
    def setUp(self):
        self.service = LiviaAssistantService()

    def test_new_cycle_does_not_leak_previous_visitor_name_in_provider_history(self):
        conversation = self.service.get_or_create_conversation(session_key="lorena-provider-history")
        conversation.visitor_name = "Lorena"
        conversation.save(update_fields=["visitor_name", "updated_at"])
        LiviaLeadCapture.objects.create(
            conversation=conversation,
            name="Lorena",
            email="lorena@old.com",
            phone="11988887777",
            company="Empresa Lorena",
            city="Campinas",
            is_qualified=True,
            operational_status=LiviaLeadCapture.OperationalStatus.SENT_TO_CRM,
            crm_reference={"notification_sent_at": "2026-01-01T00:00:00Z"},
        )
        self.service.register_user_message(
            conversation,
            "quero criar um app para artesanato e transformar fotos em arte",
        )
        client = RecordingClient()
        with patch("apps.livia_assistant.services.get_livia_ai_client", return_value=client):
            response = self.service.generate_response(
                conversation,
                "quero criar um app para artesanato e transformar fotos em arte",
            )
        self.assertNotIn("lorena", response.reply.lower())
        history_blob = " ".join((message.get("content") or "").lower() for message in (client.messages or []))
        self.assertNotIn("lorena", history_blob)

    def test_name_correction_clears_inherited_name_without_saving_celular_as_city(self):
        conversation = self.service.get_or_create_conversation(session_key="name-correction-service")
        conversation.visitor_name = "Lorena"
        conversation.save(update_fields=["visitor_name", "updated_at"])
        lead = LiviaLeadCapture.objects.create(
            conversation=conversation,
            name="Lorena",
            company="Empresa X",
            city="Campinas",
        )
        text = "celular, mas Livia eu não sou a Lorena nem conheço e ainda não te falei meu nome"
        self.service.register_user_message(conversation, text)
        extracted = self.service.extract_lead_data(text, conversation=conversation)
        updated = self.service.create_or_update_lead_capture(conversation, extracted, explicit_lead=lead)
        self.assertEqual(updated.name, "")
        self.assertNotEqual((updated.city or "").lower(), "celular")
        self.assertNotEqual((updated.company or "").lower(), "celular")
        conversation.refresh_from_db()
        self.assertEqual(conversation.visitor_name, "")

    def test_discovery_device_answer_does_not_extract_city(self):
        conversation = self.service.get_or_create_conversation(session_key="celular-not-city-service")
        self.service.register_user_message(conversation, "quero um app para artesanato")
        self.service.register_assistant_message(conversation, "Você pretende usar no celular, tablet ou computador?")
        extracted = self.service.extract_lead_data("celular", conversation=conversation)
        self.assertEqual(extracted["city"], "")

    def test_long_discovery_phrase_does_not_extract_city(self):
        text = "faço tudo em caderno de anotação as vezes acho que to na idade da pedra"
        extracted = self.service.extract_lead_data(text)
        self.assertEqual(extracted["city"], "")
        self.assertTrue(extracted["notes"])

    def test_livia_does_not_return_to_name_after_capture_complete(self):
        conversation = self.service.get_or_create_conversation(session_key="andreia-capture-loop")
        lead = LiviaLeadCapture.objects.create(
            conversation=conversation,
            service_interest="desenvolvimento de sistema e aplicativo para celular",
            notes="pet shop precisa organizar contatos, medicamentos, banhos e follow-up pelo celular",
        )
        self.service.register_assistant_message(conversation, "Para avançar, posso saber seu nome?")

        with patch("apps.livia_assistant.services.LiviaCRMBridge.create_or_update_crm_lead"):
            for text in (
                "Andreia",
                "11945688457",
                "andreia@gnv.com.br",
                "pet gtv",
                "Rio Claro",
            ):
                self.service.register_user_message(conversation, text)
                extracted = self.service.extract_lead_data(text, conversation=conversation)
                lead = self.service.create_or_update_lead_capture(
                    conversation,
                    extracted,
                    explicit_lead=lead,
                )
                self.service.register_assistant_message(
                    conversation,
                    self.service.build_progressive_lead_reply(lead),
                )

        lead.refresh_from_db()
        self.assertEqual(lead.name, "Andreia")
        self.assertEqual(lead.company, "pet gtv")
        self.assertEqual(lead.phone, "11945688457")
        self.assertEqual(lead.email, "andreia@gnv.com.br")
        self.assertEqual(lead.city, "Rio Claro")
        self.assertEqual(self.service._expected_lead_field(conversation), "")

        final_reply = self.service.build_progressive_lead_reply(lead).lower()
        self.assertNotIn("como posso te chamar", final_reply)
        self.assertNotIn("qual seu nome", final_reply)
        self.assertNotIn("para encaminhar seu pedido, como posso te chamar", final_reply)

    def test_livia_does_not_capture_product_answer_as_contact_name_before_name_step(self):
        conversation = self.service.get_or_create_conversation(session_key="liro-not-name")
        lead = None

        for text in (
            "vi um robô e gostaria de informações",
            "esse robô pode ficar perto de crianças?",
            "acho que liro",
        ):
            self.service.register_user_message(conversation, text)
            extracted = self.service.extract_lead_data(text, conversation=conversation)
            lead = self.service.create_or_update_lead_capture(conversation, extracted, explicit_lead=lead)

        lead.refresh_from_db()
        self.assertEqual(lead.name, "")

        self.service.register_user_message(conversation, "quero orçamento")
        extracted = self.service.extract_lead_data("quero orçamento", conversation=conversation)
        lead = self.service.create_or_update_lead_capture(conversation, extracted, explicit_lead=lead)
        reply = self.service.build_progressive_lead_reply(lead).lower()

        self.assertEqual(lead.name, "")
        self.assertIn("como posso te chamar", reply)

    def test_marmoraria_summary_mentions_operational_needs(self):
        from apps.livia_assistant.discovery import build_digital_product_interest_summary

        summary = build_digital_product_interest_summary(
            "marmoraria controle de estoque clientes vendas captação de contatos"
        )
        lowered = summary.lower()
        self.assertIn("marmoraria", lowered)
        self.assertIn("estoque", lowered)
        self.assertIn("clientes", lowered)
        self.assertIn("vendas", lowered)
        self.assertNotIn("smart360", lowered)
        self.assertNotIn("solução solicitada", lowered)

    def test_artesanato_summary_mentions_photos_and_clients(self):
        from apps.livia_assistant.discovery import build_digital_product_interest_summary

        summary = build_digital_product_interest_summary(
            "app artesanato transformar foto em arte cadastro de clientes"
        )
        lowered = summary.lower()
        self.assertTrue(any(term in lowered for term in ("artesanato", "arte", "aplicativo", "sistema")))
        self.assertTrue(any(term in lowered for term in ("foto", "fotos", "clientes")))
        self.assertNotIn("smart360", lowered)
        self.assertNotIn("solução solicitada", lowered)
