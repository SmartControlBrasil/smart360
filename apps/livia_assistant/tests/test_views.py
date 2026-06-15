import json
import os
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.growth_engine.models import Lead
from apps.livia_assistant.models import LiviaConversation, LiviaLeadCapture, LiviaMessage
from apps.livia_assistant.services import LiviaAssistantService


class LiviaChatEndpointTests(TestCase):
    def test_chat_endpoint_returns_valid_json(self):
        response = self.client.post(
            reverse("livia_assistant:chat"),
            data=json.dumps(
                {
                    "message": "quero orçamento para PMOC em São Paulo, meu telefone é 11999999999",
                    "session_key": "public-session-1",
                    "source_page": "/contato/",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("conversation_id", payload)
        self.assertIn("reply", payload)
        self.assertTrue(payload["lead_detected"])
        self.assertFalse(payload["handoff_recommended"])
        self.assertEqual(LiviaConversation.objects.count(), 1)
        self.assertEqual(LiviaMessage.objects.count(), 2)
        self.assertTrue(LiviaMessage.objects.filter(role=LiviaMessage.Role.ASSISTANT).exists())
        self.assertEqual(LiviaLeadCapture.objects.count(), 1)

    def test_chat_endpoint_recommends_handoff_for_emergency(self):
        response = self.client.post(
            reverse("livia_assistant:chat"),
            data=json.dumps(
                {
                    "message": "Está saindo fumaça e cheiro de queimado do painel",
                    "session_key": "public-session-2",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["handoff_recommended"])

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_chat_endpoint_works_with_fallback_provider(self):
        response = self.client.post(
            reverse("livia_assistant:chat"),
            data=json.dumps({"message": "Olá", "session_key": "fallback-session"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("reply", response.json())

    @override_settings(LIVIA_AI_PROVIDER="openai", OPENAI_API_KEY="")
    def test_chat_endpoint_falls_back_when_openai_key_is_missing(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            response = self.client.post(
                reverse("livia_assistant:chat"),
                data=json.dumps({"message": "Olá", "session_key": "openai-no-key"}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("reply", response.json())
        self.assertEqual(LiviaMessage.objects.filter(role=LiviaMessage.Role.ASSISTANT).count(), 1)

    def test_chat_endpoint_rejects_empty_payload(self):
        response = self.client.post(
            reverse("livia_assistant:chat"),
            data=json.dumps({}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_chat_endpoint_rejects_long_message(self):
        response = self.client.post(
            reverse("livia_assistant:chat"),
            data=json.dumps({"message": "x" * 2001}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("2000", response.json()["error"])

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_chat_flow_collects_one_field_at_a_time_and_persists_progress(self):
        mail.outbox.clear()
        session_key = "commercial-sequence-real-flow"
        url = reverse("livia_assistant:chat")

        first = self.client.post(
            url,
            data=json.dumps({"message": "quero um diagnóstico", "session_key": session_key}),
            content_type="application/json",
        )
        first_reply = first.json()["reply"].lower()
        self.assertIn("como posso te chamar", first_reply)
        self.assertNotIn("telefone/whatsapp", first_reply)
        self.assertNotIn("e-mail", first_reply)

        second = self.client.post(
            url,
            data=json.dumps({"message": "Marcelo", "session_key": session_key}),
            content_type="application/json",
        )
        capture = LiviaLeadCapture.objects.get(conversation__session_key=session_key)
        self.assertEqual(capture.name, "Marcelo")
        self.assertEqual(capture.company, "")
        self.assertIn("nome da empresa", second.json()["reply"].lower())

        third = self.client.post(
            url,
            data=json.dumps({"message": "Smart Control", "session_key": session_key}),
            content_type="application/json",
        )
        capture.refresh_from_db()
        self.assertEqual(capture.company, "Smart Control")
        self.assertIn("qual cidade", third.json()["reply"].lower())
        self.assertNotIn("e-mail", third.json()["reply"].lower())

        fourth = self.client.post(
            url,
            data=json.dumps({"message": "Itapevi", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertIn("telefone/whatsapp", fourth.json()["reply"].lower())

        fifth = self.client.post(
            url,
            data=json.dumps({"message": "11 962196100", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertIn("e-mail", fifth.json()["reply"].lower())

        sixth = self.client.post(
            url,
            data=json.dumps({"message": "marcelo@smartcontrol.com.br", "session_key": session_key}),
            content_type="application/json",
        )
        capture.refresh_from_db()
        self.assertEqual(capture.phone, "11 962196100")
        self.assertEqual(capture.email, "marcelo@smartcontrol.com.br")
        self.assertTrue(capture.is_qualified)
        self.assertTrue(sixth.json()["lead_registered"])
        self.assertIn("vou encaminhar seu pedido", sixth.json()["reply"].lower())
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

        technical = self.client.post(
            url,
            data=json.dumps({"message": "O que é FMEA?", "session_key": session_key}),
            content_type="application/json",
        )
        technical_reply = technical.json()["reply"].lower()
        self.assertIn("fmea", technical_reply)
        self.assertNotIn("como posso te chamar", technical_reply)
        self.assertNotIn("telefone/whatsapp", technical_reply)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_technical_electronic_board_request_does_not_start_lead_capture(self):
        response = self.client.post(
            reverse("livia_assistant:chat"),
            data=json.dumps({"message": "preciso fazer uma placa eletrônica", "session_key": "technical-board"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["lead_detected"])
        self.assertNotIn("como posso te chamar", response.json()["reply"].lower())
        self.assertFalse(LiviaLeadCapture.objects.filter(conversation__session_key="technical-board").exists())

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_simple_name_answers_are_persisted_and_advance_to_company(self):
        url = reverse("livia_assistant:chat")
        for index, name in enumerate(("Antonio", "Marcelo", "João da Silva", "Antonio Carlos")):
            with self.subTest(name=name):
                session_key = f"simple-name-{index}"
                first = self.client.post(
                    url,
                    data=json.dumps({"message": "quero um orçamento", "session_key": session_key}),
                    content_type="application/json",
                )
                self.assertIn("como posso te chamar", first.json()["reply"].lower())

                second = self.client.post(
                    url,
                    data=json.dumps({"message": name, "session_key": session_key}),
                    content_type="application/json",
                )
                capture = LiviaLeadCapture.objects.get(conversation__session_key=session_key)
                self.assertEqual(capture.name, name)
                self.assertIn("nome da empresa", second.json()["reply"].lower())
                self.assertNotIn("como posso te chamar", second.json()["reply"].lower())

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_endpoint_replaces_provider_multi_field_request_with_single_question(self):
        url = reverse("livia_assistant:chat")
        bad_reply = "Por favor, me informe seu nome, empresa, telefone, e-mail e cidade."

        with patch("apps.livia_assistant.services.get_livia_ai_client") as client_factory:
            client_factory.return_value.generate_reply.return_value = bad_reply
            response = self.client.post(
                url,
                data=json.dumps({"message": "Quero um orçamento", "session_key": "bad-provider-reply"}),
                content_type="application/json",
            )

        reply = response.json()["reply"].lower()
        self.assertIn("como posso te chamar", reply)
        self.assertNotIn("empresa", reply)
        self.assertNotIn("telefone", reply)
        self.assertNotIn("e-mail", reply)
        self.assertNotIn("cidade", reply)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_duno_supermarket_flow_qualifies_with_context_summary_without_redundant_questions(self):
        mail.outbox.clear()
        session_key = "duno-supermarket-qualified-flow"
        url = reverse("livia_assistant:chat")

        technical_messages = [
            "Quero um robô para supermercado em São Paulo",
            "A função é limpeza",
            "A área tem 12.000 m²",
            "A operação será no período noturno",
            "Não possui infraestrutura de automação atual",
            "O Duno atende esse cenário?",
        ]
        for message in technical_messages:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        accepted = self.client.post(
            url,
            data=json.dumps({"message": "Pode encaminhar meu pedido", "session_key": session_key}),
            content_type="application/json",
        )
        accepted_reply = accepted.json()["reply"].lower()
        self.assertTrue(
            any(
                marker in accepted_reply
                for marker in (
                    "como posso te chamar",
                    "em qual empresa",
                    "nome da empresa",
                    "telefone/whatsapp",
                )
            )
        )

        name = self.client.post(
            url,
            data=json.dumps({"message": "Marcos Antonio", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertIn("nome da empresa", name.json()["reply"].lower())
        self.assertNotIn("telefone", name.json()["reply"].lower())

        company = self.client.post(
            url,
            data=json.dumps({"message": "Gocil", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertTrue(
            any(
                marker in company.json()["reply"].lower()
                for marker in ("em qual cidade", "telefone/whatsapp")
            )
        )
        self.assertNotIn("e-mail", company.json()["reply"].lower())

        if "em qual cidade" in company.json()["reply"].lower():
            city = self.client.post(
                url,
                data=json.dumps({"message": "São Paulo", "session_key": session_key}),
                content_type="application/json",
            )
            self.assertIn("telefone/whatsapp", city.json()["reply"].lower())

        phone = self.client.post(
            url,
            data=json.dumps({"message": "11923456789", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertIn("e-mail", phone.json()["reply"].lower())

        qualified = self.client.post(
            url,
            data=json.dumps({"message": "marcos@gocil.com.br", "session_key": session_key}),
            content_type="application/json",
        )
        expected = (
            "Perfeito, Marcos. Vou encaminhar seu pedido para nossa equipe com este resumo: "
            "robô Duno para limpeza noturna em supermercado de aproximadamente 12.000 m², "
            "sem infraestrutura de automação atual, em São Paulo. "
            "Um especialista da Smart Control Brasil entrará em contato."
        )
        self.assertEqual(qualified.json()["reply"], expected)
        self.assertTrue(qualified.json()["lead_registered"])
        self.assertNotIn("qual serviço", qualified.json()["reply"].lower())
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Duno", mail.outbox[0].body)
        self.assertIn("12.000 m²", mail.outbox[0].body)

        capture = LiviaLeadCapture.objects.get(conversation__session_key=session_key)
        self.assertEqual(capture.name, "Marcos Antonio")
        self.assertEqual(capture.company, "Gocil")
        self.assertEqual(capture.phone, "11923456789")
        self.assertEqual(capture.email, "marcos@gocil.com.br")
        self.assertEqual(capture.city, "São Paulo")
        self.assertEqual(capture.service_interest, "Duno - robô de limpeza")
        for context in ("Duno", "limpeza", "supermercado", "12.000 m²", "noturno", "infraestrutura", "São Paulo"):
            self.assertIn(context.lower(), capture.notes.lower())

        crm_lead = Lead.objects.get()
        self.assertEqual(crm_lead.contact_name, "Marcos Antonio")
        self.assertIn("Duno", crm_lead.notes)
        self.assertIn("12.000 m²", crm_lead.notes)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_chat_flow_creates_growth_lead_and_returns_confirmation(self):
        session_key = "chat-create-growth-lead"
        url = reverse("livia_assistant:chat")

        self.client.post(
            url,
            data=json.dumps({"message": "quero um diagnóstico", "session_key": session_key}),
            content_type="application/json",
        )
        self.client.post(
            url,
            data=json.dumps(
                {
                    "message": "meu nome é Marcelo, sou da Smart Control, Itapevi, telefone 11999999999",
                    "session_key": session_key,
                }
            ),
            content_type="application/json",
        )
        final = self.client.post(
            url,
            data=json.dumps(
                {
                    "message": "email marcelo@smartcontrol.com.br e problema: paradas recorrentes na linha de embalagem",
                    "session_key": session_key,
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(final.status_code, 200)
        payload = final.json()
        self.assertTrue(payload["lead_registered"])
        self.assertIn("vou encaminhar seu pedido", payload["reply"].lower())
        self.assertIn("especialista da smart control brasil", payload["reply"].lower())
        self.assertEqual(Lead.objects.count(), 1)
        lead = Lead.objects.first()
        self.assertEqual(lead.email, "marcelo@smartcontrol.com.br")
        self.assertEqual(lead.phone, "11999999999")
        self.assertEqual(lead.city.lower(), "itapevi")
        self.assertEqual((lead.metadata or {}).get("source"), "livia_assistant")

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_chat_flow_repeated_email_does_not_duplicate_growth_lead(self):
        session_a = "chat-dup-email-a"
        session_b = "chat-dup-email-b"
        url = reverse("livia_assistant:chat")

        messages = [
            "quero um diagnóstico",
            "meu nome é Ana, sou da Empresa Alfa, cidade Campinas, telefone 11911112222",
            "email ana@empresa.com e problema falha recorrente na linha",
        ]
        for msg in messages:
            self.client.post(
                url,
                data=json.dumps({"message": msg, "session_key": session_a}),
                content_type="application/json",
            )
        for msg in [
            "quero um diagnóstico",
            "meu nome é Ana 2, sou da Empresa Beta, cidade Campinas, telefone 11933334444",
            "email ana@empresa.com e problema parada na esteira",
        ]:
            self.client.post(
                url,
                data=json.dumps({"message": msg, "session_key": session_b}),
                content_type="application/json",
            )

        self.assertEqual(Lead.objects.count(), 1)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_new_subject_after_qualified_lead_starts_new_cycle_without_context_leak(self):
        mail.outbox.clear()
        session_key = "chat-isolated-cycle-after-qualified"
        url = reverse("livia_assistant:chat")

        first_cycle_messages = [
            "quero um robô de limpeza para supermercado",
            "supermercado em São Paulo",
            "empresa Gocil",
            "meu nome é Marcos",
            "São Paulo",
            "telefone 11923456789",
            "marcos@gocil.com.br",
        ]
        for message in first_cycle_messages:
            self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )

        first_lead = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertIsNotNone(first_lead)
        self.assertTrue(first_lead.is_qualified)
        self.assertEqual(first_lead.operational_status, LiviaLeadCapture.OperationalStatus.SENT_TO_CRM)
        self.assertIn("notification_sent_at", first_lead.crm_reference)
        self.assertEqual(len(mail.outbox), 1)
        first_email_body = mail.outbox[-1].body.lower()
        self.assertIn("gocil", first_email_body)
        self.assertIn("limpeza", first_email_body)

        new_subject = self.client.post(
            url,
            data=json.dumps(
                {"message": "preciso fazer uma placa eletrônica", "session_key": session_key}
            ),
            content_type="application/json",
        )
        self.assertEqual(new_subject.status_code, 200)
        new_reply = new_subject.json()["reply"].lower()
        self.assertNotIn("gocil", new_reply)
        self.assertNotIn("supermercado", new_reply)
        self.assertNotIn("duno", new_reply)

        self.client.post(
            url,
            data=json.dumps({"message": "meu nome é Carla", "session_key": session_key}),
            content_type="application/json",
        )
        self.client.post(
            url,
            data=json.dumps({"message": "sou da Eletro Nova", "session_key": session_key}),
            content_type="application/json",
        )
        self.client.post(
            url,
            data=json.dumps({"message": "telefone 11988776655", "session_key": session_key}),
            content_type="application/json",
        )
        self.client.post(
            url,
            data=json.dumps({"message": "Campinas", "session_key": session_key}),
            content_type="application/json",
        )
        self.client.post(
            url,
            data=json.dumps({"message": "carla@eletronova.com.br", "session_key": session_key}),
            content_type="application/json",
        )

        captures = list(LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("created_at", "id"))
        self.assertEqual(len(captures), 2)
        second_lead = captures[1]

        self.assertEqual(second_lead.name.lower(), "carla")
        self.assertEqual(second_lead.company.lower(), "eletro nova")
        self.assertEqual(second_lead.phone, "11988776655")
        self.assertNotIn("gocil", second_lead.notes.lower())
        self.assertNotIn("supermercado", second_lead.notes.lower())
        self.assertNotIn("duno", second_lead.notes.lower())
        self.assertIn("placa eletrônica", second_lead.notes.lower())

        self.assertEqual(len(mail.outbox), 2)
        second_email_body = mail.outbox[-1].body.lower()
        self.assertIn("carla", second_email_body)
        self.assertIn("eletro nova", second_email_body)
        self.assertIn("placa eletrônica", second_email_body)
        self.assertNotIn("gocil", second_email_body)
        self.assertNotIn("supermercado", second_email_body)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_progressive_collection_persists_company_and_keeps_notes_technical_only(self):
        mail.outbox.clear()
        session_key = "progressive-collection-company-persistence"
        url = reverse("livia_assistant:chat")

        flow = [
            "Quero um robô para supermercado",
            "limpeza",
            "12000 m²",
            "não possui infraestrutura",
            "sim",
            "meu nome é Marcos Silva",
            "empresa govip",
            "São Paulo",
            "11962196100",
            "Marcos",
        ]
        for message in flow:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertIsNotNone(capture)
        self.assertEqual(capture.name, "Marcos Silva")
        self.assertEqual(capture.company, "govip")
        self.assertEqual(capture.city, "São Paulo")
        self.assertEqual(capture.phone, "11962196100")
        self.assertEqual(capture.email, "")
        self.assertFalse(capture.is_qualified)
        self.assertEqual(capture.operational_status, LiviaLeadCapture.OperationalStatus.NEW)

        notes = (capture.notes or "").lower()
        self.assertIn("robô para supermercado", notes)
        self.assertIn("limpeza", notes)
        self.assertIn("12000 m²", notes)
        self.assertNotIn("marcos silva", notes)
        self.assertNotIn("govip", notes)
        self.assertNotIn("11962196100", notes)
        self.assertNotIn("marcos@govip.com", notes)

        self.assertEqual(len(mail.outbox), 0)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_post_qualification_optional_email_and_city_update_without_new_notification(self):
        mail.outbox.clear()
        session_key = "post-qualified-optional-fields"
        url = reverse("livia_assistant:chat")

        initial_flow = [
            "quero orçamento",
            "meu nome é Marcos",
            "sou da Govip",
            "São Paulo",
            "11962196100",
            "marcos@govip.com",
        ]
        for message in initial_flow:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        first_capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertIsNotNone(first_capture)
        self.assertTrue(first_capture.is_qualified)
        self.assertEqual(first_capture.operational_status, LiviaLeadCapture.OperationalStatus.SENT_TO_CRM)
        self.assertEqual(len(mail.outbox), 1)

        offer_city = self.client.post(
            url,
            data=json.dumps({"message": "quer saber qual minha cidade?", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(offer_city.status_code, 200)
        self.assertIn("pode me informar a cidade, eu adiciono ao atendimento", offer_city.json()["reply"].lower())
        self.assertNotIn("telefone/whatsapp", offer_city.json()["reply"].lower())

        provide_city = self.client.post(
            url,
            data=json.dumps({"message": "São Paulo", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(provide_city.status_code, 200)

        close_message = self.client.post(
            url,
            data=json.dumps({"message": "ok", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(close_message.status_code, 200)
        self.assertIn("atendimento registrado e atualizado", close_message.json()["reply"].lower())

        updated_capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertEqual(updated_capture.email, "marcos@govip.com")
        self.assertEqual(updated_capture.city.lower(), "são paulo")
        self.assertEqual(updated_capture.phone, "11962196100")
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_flow_without_email_does_not_qualify_and_then_qualifies_after_email(self):
        mail.outbox.clear()
        session_key = "requires-email-qualification"
        url = reverse("livia_assistant:chat")

        messages = [
            "quero um diagnóstico",
            "João",
            "Arteb",
            "São Paulo",
            "1156487854",
        ]
        for message in messages:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        pre_email_capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertFalse(pre_email_capture.is_qualified)
        self.assertEqual(pre_email_capture.email, "")
        self.assertEqual(len(mail.outbox), 0)

        ask_email_reply = self.client.post(
            url,
            data=json.dumps({"message": "ok", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(ask_email_reply.status_code, 200)
        self.assertIn("e-mail", ask_email_reply.json()["reply"].lower())
        self.assertNotIn("telefone/whatsapp", ask_email_reply.json()["reply"].lower())

        send_email = self.client.post(
            url,
            data=json.dumps({"message": "joao@arteb.com.br", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(send_email.status_code, 200)

        final_capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertTrue(final_capture.is_qualified)
        self.assertEqual(final_capture.email, "joao@arteb.com.br")
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_name_and_phone_only_does_not_qualify_and_keeps_collecting_required_fields(self):
        mail.outbox.clear()
        session_key = "scenario-a-name-phone-only"
        url = reverse("livia_assistant:chat")

        self.client.post(
            url,
            data=json.dumps({"message": "quero um diagnóstico", "session_key": session_key}),
            content_type="application/json",
        )
        self.client.post(
            url,
            data=json.dumps({"message": "meu nome é Valmir", "session_key": session_key}),
            content_type="application/json",
        )
        response = self.client.post(
            url,
            data=json.dumps({"message": "1145784512", "session_key": session_key}),
            content_type="application/json",
        )
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertFalse(capture.is_qualified)
        self.assertEqual(capture.name, "Valmir")
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("nome da empresa", response.json()["reply"].lower())

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_name_phone_company_without_city_email_asks_city(self):
        mail.outbox.clear()
        session_key = "scenario-b-no-city-email"
        url = reverse("livia_assistant:chat")
        flow = ["quero um diagnóstico", "meu nome é Valmir", "empresa Arteb", "1145784512"]
        last_response = None
        for message in flow:
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertFalse(capture.is_qualified)
        self.assertEqual(capture.company, "Arteb")
        self.assertEqual(capture.city, "")
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("qual cidade", last_response.json()["reply"].lower())

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_name_phone_company_city_without_email_asks_email(self):
        mail.outbox.clear()
        session_key = "scenario-c-no-email"
        url = reverse("livia_assistant:chat")
        flow = ["quero um diagnóstico", "meu nome é Valmir", "empresa Arteb", "São Paulo", "1145784512"]
        last_response = None
        for message in flow:
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertFalse(capture.is_qualified)
        self.assertEqual(capture.city, "São Paulo")
        self.assertEqual(capture.email, "")
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("qual e-mail", last_response.json()["reply"].lower())

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_all_five_fields_valid_sends_single_notification(self):
        mail.outbox.clear()
        session_key = "scenario-d-all-fields"
        url = reverse("livia_assistant:chat")
        flow = [
            "quero um diagnóstico",
            "meu nome é Valmir",
            "empresa Arteb",
            "São Paulo",
            "1145784512",
            "valmir@arteb.com.br",
        ]
        for message in flow:
            self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertTrue(capture.is_qualified)
        self.assertEqual(capture.operational_status, LiviaLeadCapture.OperationalStatus.SENT_TO_CRM)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_generic_acceptance_response_is_not_saved_as_company(self):
        mail.outbox.clear()
        session_key = "scenario-e-sim-gostaria-not-company"
        url = reverse("livia_assistant:chat")
        self.client.post(
            url,
            data=json.dumps({"message": "quero um diagnóstico", "session_key": session_key}),
            content_type="application/json",
        )
        self.client.post(
            url,
            data=json.dumps({"message": "meu nome é Valmir", "session_key": session_key}),
            content_type="application/json",
        )
        response = self.client.post(
            url,
            data=json.dumps({"message": "sim gostaria", "session_key": session_key}),
            content_type="application/json",
        )
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertEqual(capture.company, "")
        self.assertFalse(capture.is_qualified)
        self.assertIn("nome da empresa", response.json()["reply"].lower())

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_compact_full_message_qualifies_with_all_required_fields(self):
        mail.outbox.clear()
        session_key = "compact-full-message"
        url = reverse("livia_assistant:chat")

        response = self.client.post(
            url,
            data=json.dumps(
                {
                    "message": "João, Arteb, São Paulo, 1156487854, joao@arteb.com.br",
                    "session_key": session_key,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertTrue(capture.is_qualified)
        self.assertEqual(capture.name.lower(), "joão")
        self.assertEqual(capture.company.lower(), "arteb")
        self.assertEqual(capture.phone, "1156487854")
        self.assertEqual(capture.email, "joao@arteb.com.br")
        self.assertEqual(capture.city.lower(), "são paulo")
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_city_before_phone_is_persisted_and_required_for_qualification(self):
        mail.outbox.clear()
        session_key = "city-before-phone"
        url = reverse("livia_assistant:chat")

        flow = [
            "quero falar com especialista",
            "João",
            "Arteb",
            "São Paulo",
            "1156487854",
            "joao@arteb.com.br",
        ]
        for message in flow:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertEqual(capture.city.lower(), "são paulo")
        self.assertTrue(capture.is_qualified)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_long_intent_then_phone_only_does_not_notify(self):
        mail.outbox.clear()
        session_key = "long-intent-then-phone-no-notify"
        url = reverse("livia_assistant:chat")

        first = self.client.post(
            url,
            data=json.dumps(
                {
                    "message": "oi preciso de uma empresa de automação para cuidar dos meus equipamentos",
                    "session_key": session_key,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)

        after_phone = self.client.post(
            url,
            data=json.dumps({"message": "1145787845", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(after_phone.status_code, 200)

        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertEqual(capture.name, "")
        self.assertEqual(capture.company, "")
        self.assertEqual(capture.phone, "1145787845")
        self.assertFalse(capture.is_qualified)
        self.assertFalse(after_phone.json()["lead_registered"])
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_weiss_climatic_flow_does_not_qualify_or_forward_prematurely(self):
        mail.outbox.clear()
        session_key = "real-flow-weiss-climatic"
        url = reverse("livia_assistant:chat")
        flow = [
            "voces consertam equipamentos?",
            "uma camara climatica",
            "não gela",
            "weiss",
            "sim low pressure",
            "ainda não",
            "sim gostaria",
            "Valmir",
            "1145784512",
        ]
        last_response = None
        for message in flow:
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertIsNotNone(capture)
        self.assertFalse(capture.is_qualified)
        self.assertNotEqual(capture.operational_status, LiviaLeadCapture.OperationalStatus.SENT_TO_CRM)
        self.assertNotEqual(capture.company.lower(), "sim gostaria")
        self.assertEqual(len(mail.outbox), 0)
        reply = last_response.json()["reply"].lower()
        self.assertNotIn("vou encaminhar", reply)
        self.assertTrue(
            "em qual cidade" in reply
            or "qual cidade" in reply
            or "nome da empresa" in reply
            or "qual e-mail" in reply
            or "como posso te chamar" in reply,
            msg=reply,
        )

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_votsch_thermal_shock_flow_does_not_forward_without_city_and_email(self):
        mail.outbox.clear()
        session_key = "real-flow-votsch-thermal-shock"
        url = reverse("livia_assistant:chat")
        flow = [
            "minha maquina parou",
            "o painel parou de um choque termico",
            "não entendo, preciso de atendimento",
            "ja falei, o painel do choque termico apagou",
            "quero solicitar um atendimento",
            "para o choque termico",
            "um equipamento chamado choque termico da marca Votsch",
            "sim ele apagou o painel",
            "quero um atendimento, pode agendar uma visita?",
            "Marcelo",
            "control lab",
            "11 78457878",
        ]
        last_response = None
        for message in flow:
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertIsNotNone(capture)
        self.assertFalse(capture.is_qualified)
        self.assertNotEqual(capture.operational_status, LiviaLeadCapture.OperationalStatus.SENT_TO_CRM)
        self.assertEqual(len(mail.outbox), 0)
        reply = last_response.json()["reply"].lower()
        self.assertNotIn("vou encaminhar", reply)
        self.assertTrue("em qual cidade" in reply or "qual cidade" in reply or "qual e-mail" in reply, msg=reply)
        summary = LiviaAssistantService()._build_technical_service_summary(capture).lower()
        self.assertNotIn("solução solicitada, em quero um atendimento", summary)
        self.assertTrue("choque" in summary, msg=summary)
        self.assertTrue("votsch" in summary or "vötsch" in summary, msg=summary)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_complete_technical_flow_with_all_fields_qualifies_and_forwards(self):
        mail.outbox.clear()
        session_key = "real-flow-complete-technical"
        url = reverse("livia_assistant:chat")
        flow = [
            "minha camara climatica weiss nao gela",
            "sim low pressure",
            "quero atendimento tecnico",
            "meu nome é Valmir",
            "empresa Arteb",
            "São Paulo",
            "1145784512",
            "valmir@arteb.com.br",
        ]
        for message in flow:
            self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertTrue(capture.is_qualified)
        self.assertEqual(capture.operational_status, LiviaLeadCapture.OperationalStatus.SENT_TO_CRM)
        self.assertEqual(len(mail.outbox), 1)
        summary = LiviaAssistantService().build_qualified_lead_reply(capture).lower()
        self.assertIn("câmara climática", summary)
        self.assertIn("weiss", summary)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_frigorifica_flow_preserves_company_and_technical_summary(self):
        mail.outbox.clear()
        session_key = "real-flow-frigorifica-buffet"
        url = reverse("livia_assistant:chat")
        flow = [
            "estou com problemas em um equipamento que parou!!!",
            "Uma camara frigorifica",
            "tem acumulo de gelo no ventilador",
            "não tenho contrato gostaria de uma avaliação e para possivel contrato",
            "José",
            "buffet arroz e festa",
            "1196457845",
            "Osasco",
            "arroz@gmail.com",
        ]
        after_company = None
        after_phone = None
        last_response = None
        for index, message in enumerate(flow, start=1):
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
            if index == 6:
                after_company = capture
            if index == 7:
                after_phone = last_response

        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertIsNotNone(after_company)
        self.assertEqual(after_company.company, "buffet arroz e festa")
        self.assertNotIn("ja falei", (capture.company or "").lower())
        self.assertNotIn("já falei", (capture.company or "").lower())

        phone_reply = after_phone.json()["reply"].lower()
        self.assertNotIn("nome da empresa", phone_reply)
        self.assertTrue("em qual cidade" in phone_reply or "qual cidade" in phone_reply, msg=phone_reply)

        self.assertTrue(capture.is_qualified)
        self.assertEqual(capture.operational_status, LiviaLeadCapture.OperationalStatus.SENT_TO_CRM)

        notes = (capture.notes or "").lower()
        self.assertTrue("gelo" in notes or "ventilador" in notes, msg=notes)
        self.assertTrue("avali" in notes or "contrato" in notes, msg=notes)

        final_reply = last_response.json()["reply"].lower()
        self.assertTrue("frigorifica" in final_reply or "frigorífica" in final_reply, msg=final_reply)
        self.assertTrue("gelo" in final_reply or "ventilador" in final_reply, msg=final_reply)
        self.assertNotIn("solução solicitada, em osasco", final_reply)
