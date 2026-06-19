import json
import os
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.growth_engine.models import Lead
from apps.livia_assistant.models import LiviaConversation, LiviaLeadCapture, LiviaMessage
from apps.livia_assistant.qualification import is_lead_ready_for_notification
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
    def test_clear_technical_issue_answers_before_asking_name(self):
        response = self.client.post(
            reverse("livia_assistant:chat"),
            data=json.dumps({"message": "Minha IHM apagou", "session_key": "ihm-apagou-tech-first"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        reply = response.json()["reply"].lower()
        self.assertLess(reply.index("quando uma ihm apaga"), reply.index("como posso te chamar"))
        self.assertIn("técnico habilitado", reply)
        self.assertIn("somente a ihm", reply)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_ai_spreadsheet_reply_qualifies_data_quality_first(self):
        response = self.client.post(
            reverse("livia_assistant:chat"),
            data=json.dumps({"message": "Tenho uma planilha e quero usar IA para prever falhas", "session_key": "ia-planilha"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        reply = response.json()["reply"]
        self.assertIn("Dá para avaliar o uso de IA, mas primeiro precisamos analisar a qualidade dos dados.", reply)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_after_registered_new_question_does_not_restart_with_hello_or_duplicate_email(self):
        mail.outbox.clear()
        session_key = "registered-followup-no-duplicate"
        url = reverse("livia_assistant:chat")
        for message in [
            "Minha IHM apagou",
            "Marcelo",
            "Smart Control",
            "Itapevi",
            "11999999999",
            "marcelo@smartcontrol.com.br",
        ]:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        self.assertEqual(len(mail.outbox), 1)
        before_count = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).count()
        followup = self.client.post(
            url,
            data=json.dumps({"message": "Agora o inversor está em falha", "session_key": session_key}),
            content_type="application/json",
        )

        self.assertEqual(followup.status_code, 200)
        reply = followup.json()["reply"].lower()
        self.assertFalse(reply.startswith("olá"), msg=reply)
        self.assertIn("inversor em falha", reply)
        self.assertEqual(LiviaLeadCapture.objects.filter(conversation__session_key=session_key).count(), before_count)
        self.assertEqual(len(mail.outbox), 1)
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).first()
        history = " ".join((capture.crm_reference or {}).get("technical_history", [])).lower()
        self.assertIn("inversor", history)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_invalid_phone_does_not_qualify_and_asks_confirmation(self):
        mail.outbox.clear()
        session_key = "invalid-phone-confirmation"
        url = reverse("livia_assistant:chat")
        for message in ["Minha IHM apagou", "Marcelo", "Smart Control", "Itapevi"]:
            self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )

        response = self.client.post(
            url,
            data=json.dumps({"message": "12345", "session_key": session_key}),
            content_type="application/json",
        )
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).first()
        self.assertFalse(capture.is_qualified)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("pode confirmar com ddd", response.json()["reply"].lower())

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_invalid_email_does_not_qualify_and_asks_confirmation(self):
        mail.outbox.clear()
        session_key = "invalid-email-confirmation"
        url = reverse("livia_assistant:chat")
        for message in ["Quero orçamento para um sistema web com IA", "Marcelo", "Smart Control", "São Paulo", "11999999999"]:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        response = self.client.post(
            url,
            data=json.dumps({"message": "marcelo@", "session_key": session_key}),
            content_type="application/json",
        )
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).first()
        self.assertFalse(capture.is_qualified)
        self.assertEqual(capture.email, "")
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("parece estar fora do formato", response.json()["reply"].lower())

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_web_system_price_question_answers_scope_before_collecting_lead(self):
        mail.outbox.clear()
        session_key = "web-system-price-scope-first"
        url = reverse("livia_assistant:chat")

        first = self.client.post(
            url,
            data=json.dumps({"message": "Vocês desenvolvem sistemas web?", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)

        price = self.client.post(
            url,
            data=json.dumps({"message": "Quanto custa um sistema?", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(price.status_code, 200)
        reply = price.json()["reply"].lower()
        self.assertIn("valor depende do escopo", reply)
        self.assertIn("mvp", reply)
        self.assertNotIn("como posso te chamar", reply)

        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).first()
        self.assertIsNone(capture)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_spontaneous_phone_during_warehouse_discovery_is_saved_without_notification(self):
        mail.outbox.clear()
        session_key = "warehouse-discovery-spontaneous-phone"
        url = reverse("livia_assistant:chat")

        first = self.client.post(
            url,
            data=json.dumps(
                {
                    "message": "preciso de um sistema para meu deposito de materiais de construção",
                    "session_key": session_key,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertNotIn("como posso te chamar", first.json()["reply"].lower())

        second = self.client.post(
            url,
            data=json.dumps({"message": "11988887766", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.json()["lead_registered"])
        self.assertEqual(len(mail.outbox), 0)

        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).first()
        self.assertIsNotNone(capture)
        self.assertEqual(capture.phone, "11988887766")
        self.assertFalse(capture.is_qualified)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_web_system_quote_intent_starts_lead_collection(self):
        session_key = "web-system-quote-starts-lead"
        response = self.client.post(
            reverse("livia_assistant:chat"),
            data=json.dumps({"message": "quero orçamento para um sistema web com IA", "session_key": session_key}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        reply = response.json()["reply"].lower()
        self.assertIn("como posso te chamar", reply)
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).first()
        self.assertIsNotNone(capture)
        self.assertFalse(capture.is_qualified)
        self.assertEqual(capture.service_interest, "desenvolvimento de sistema web com IA integrada")

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_web_system_lead_summary_mentions_web_ia_not_generic_or_industrial(self):
        mail.outbox.clear()
        session_key = "web-system-summary"
        url = reverse("livia_assistant:chat")
        flow = [
            "quero orçamento para um sistema web com IA integrada para automatizar uma planilha",
            "Marcelo",
            "Smart Control",
            "São Paulo",
            "11999999999",
        ]
        last_response = None
        for message in flow:
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(last_response.status_code, 200)

        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).first()
        self.assertIsNotNone(capture)
        self.assertFalse(capture.is_qualified)
        self.assertFalse(last_response.json()["lead_registered"])
        self.assertEqual(capture.email, "")
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("qual e-mail podemos usar para formalizar o atendimento", last_response.json()["reply"].lower())

        last_response = self.client.post(
            url,
            data=json.dumps({"message": "marcelo@smartcontrol.com.br", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(last_response.status_code, 200)
        capture.refresh_from_db()
        self.assertTrue(capture.is_qualified)
        self.assertEqual(capture.email, "marcelo@smartcontrol.com.br")
        self.assertTrue(last_response.json()["lead_registered"])
        summary = (capture.notes or "").lower()
        reply = last_response.json()["reply"].lower()
        self.assertIn("sistema web com ia", summary, msg=summary)
        self.assertIn("sistema web", reply, msg=reply)
        self.assertNotIn("solução solicitada", summary)
        self.assertNotIn("máquina", summary)
        self.assertNotIn("ihm", summary)
        self.assertNotIn("em que tipo de solução", reply)
        self.assertEqual((capture.crm_reference or {}).get("category"), "sistemas_web_ia")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("E-mail: marcelo@smartcontrol.com.br", mail.outbox[0].body)
        self.assertNotIn("E-mail: Não informado", mail.outbox[0].body)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_web_system_questions_are_not_industrial_without_industrial_terms(self):
        session_key = "web-system-not-industrial"
        url = reverse("livia_assistant:chat")
        for message in [
            "Preciso transformar uma planilha em um sistema web com dashboard",
            "quero orçamento",
            "Ana",
            "Empresa Alfa",
            "Campinas",
            "11988887777",
            "ana@empresa.com.br",
        ]:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).first()
        notes = (capture.notes or "").lower()
        self.assertIn("sistema web", notes)
        self.assertNotIn("equipamento industrial", notes)
        self.assertNotIn("falha operacional", notes)
        self.assertNotIn("manutenção", notes)

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
        self.assertIn("telefone/whatsapp", third.json()["reply"].lower())
        self.assertNotIn("e-mail", third.json()["reply"].lower())

        fourth = self.client.post(
            url,
            data=json.dumps({"message": "11 962196100", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertIn("qual e-mail podemos usar para formalizar o atendimento", fourth.json()["reply"].lower())

        fifth = self.client.post(
            url,
            data=json.dumps({"message": "marcelo@smartcontrol.com.br", "session_key": session_key}),
            content_type="application/json",
        )
        capture.refresh_from_db()
        self.assertEqual(capture.phone, "11 962196100")
        self.assertEqual(capture.email, "marcelo@smartcontrol.com.br")
        self.assertFalse(capture.is_qualified)
        self.assertFalse(fifth.json()["lead_registered"])
        self.assertIn("qual cidade", fifth.json()["reply"].lower())
        self.assertEqual(Lead.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

        sixth = self.client.post(
            url,
            data=json.dumps({"message": "Itapevi", "session_key": session_key}),
            content_type="application/json",
        )
        capture.refresh_from_db()
        self.assertEqual(capture.city, "Itapevi")
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
                for marker in ("telefone/whatsapp", "em qual cidade", "qual cidade")
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
        self.assertIn("qual e-mail podemos usar para formalizar o atendimento", phone.json()["reply"].lower())
        self.assertFalse(phone.json()["lead_registered"])
        self.assertEqual(len(mail.outbox), 0)

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
        for context in ("Duno", "limpeza", "supermercado", "12.000 m²", "noturn", "infraestrutura", "São Paulo"):
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
        self.assertFalse(payload["reply"].lower().startswith("olá"))
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
    def test_new_subject_after_qualified_lead_updates_same_cycle_without_greeting(self):
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
        self.assertEqual(len(captures), 1)
        updated_lead = captures[0]

        self.assertEqual(updated_lead.name.lower(), "marcos")
        self.assertEqual(updated_lead.company.lower(), "gocil")
        history = " ".join((updated_lead.crm_reference or {}).get("technical_history", [])).lower()
        self.assertIn("placa eletrônica", history)

        self.assertEqual(len(mail.outbox), 1)

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
        ]
        last_response = None
        for message in flow:
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(last_response.status_code, 200)

        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertIsNotNone(capture)
        self.assertEqual(capture.name, "Marcos Silva")
        self.assertEqual(capture.company, "govip")
        self.assertEqual(capture.city, "São Paulo")
        self.assertEqual(capture.phone, "11962196100")
        self.assertEqual(capture.email, "")
        self.assertFalse(capture.is_qualified)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("qual e-mail podemos usar para formalizar o atendimento", last_response.json()["reply"].lower())

        email_response = self.client.post(
            url,
            data=json.dumps({"message": "marcos@govip.com", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(email_response.status_code, 200)
        capture.refresh_from_db()
        self.assertEqual(capture.email, "marcos@govip.com")
        self.assertTrue(capture.is_qualified)
        self.assertEqual(capture.operational_status, LiviaLeadCapture.OperationalStatus.SENT_TO_CRM)

        notes = (capture.notes or "").lower()
        self.assertIn("robô", notes)
        self.assertIn("limpeza", notes)
        self.assertIn("supermercado", notes)
        self.assertIn("12000 m²", notes)
        self.assertNotIn("marcos silva", notes)
        self.assertNotIn("govip", notes)
        self.assertNotIn("11962196100", notes)
        self.assertNotIn("marcos@govip.com", notes)

        self.assertEqual(len(mail.outbox), 1)

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
        self.assertFalse(offer_city.json()["lead_registered"])
        self.assertEqual(len(mail.outbox), 1)
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
    def test_flow_without_email_asks_email_without_notification(self):
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
        self.assertIn("qual e-mail podemos usar para formalizar o atendimento", response.json()["reply"].lower())

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
        self.assertIn("qual e-mail", last_response.json()["reply"].lower())

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
        self.assertIn("qual e-mail podemos usar para formalizar o atendimento", last_response.json()["reply"].lower())

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
    def test_compact_contact_without_problem_does_not_qualify(self):
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
        self.assertFalse(capture.is_qualified)
        self.assertEqual(capture.name.lower(), "joão")
        self.assertEqual(capture.company.lower(), "arteb")
        self.assertEqual(capture.phone, "1156487854")
        self.assertEqual(capture.email, "joao@arteb.com.br")
        self.assertEqual(capture.city.lower(), "são paulo")
        self.assertEqual(len(mail.outbox), 0)

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
    def test_votsch_thermal_shock_flow_qualifies_with_phone_and_description(self):
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
            "São Paulo",
            "11 78457878",
            "marcelo@controllab.com.br",
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
        self.assertTrue(capture.is_qualified)
        self.assertEqual(capture.operational_status, LiviaLeadCapture.OperationalStatus.SENT_TO_CRM)
        self.assertEqual(len(mail.outbox), 1)
        reply = last_response.json()["reply"].lower()
        self.assertIn("vou encaminhar", reply)
        summary = LiviaAssistantService()._build_technical_service_summary(capture).lower()
        self.assertNotIn("solução solicitada, em quero um atendimento", summary)
        self.assertTrue("choque" in summary, msg=summary)
        self.assertTrue("votsch" in summary or "vötsch" in summary, msg=summary)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_votsch_thermal_shock_flow_builds_structured_notes_when_qualified(self):
        mail.outbox.clear()
        session_key = "real-flow-votsch-qualified"
        url = reverse("livia_assistant:chat")
        flow = [
            "choque termico da marca Votsch",
            "painel apagou",
            "Marcelo",
            "control lab",
            "São Paulo",
            "1178457878",
            "marcelo@controllab.com.br",
        ]
        for message in flow:
            self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )

        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertTrue(capture.is_qualified)
        self.assertEqual(len(mail.outbox), 1)

        notes = (capture.notes or "").lower()
        self.assertIn("choque térmico", notes, msg=notes)
        self.assertTrue("vötsch" in notes or "votsch" in notes, msg=notes)
        self.assertTrue("painel apagou" in notes or "painel apagado" in notes, msg=notes)
        self.assertNotIn("|", capture.notes or "", msg=capture.notes)

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

        notes = (capture.notes or "").lower()
        self.assertIn("câmara climática weiss", notes, msg=notes)
        self.assertIn("não gela", notes, msg=notes)
        self.assertIn("low pressure", notes, msg=notes)

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
        self.assertIn("qual e-mail", phone_reply, msg=phone_reply)

        self.assertTrue(capture.is_qualified)
        self.assertEqual(capture.operational_status, LiviaLeadCapture.OperationalStatus.SENT_TO_CRM)

        notes = (capture.notes or "").lower()
        self.assertIn("câmara frigorífica", notes, msg=notes)
        self.assertTrue("gelo" in notes or "ventilador" in notes, msg=notes)
        self.assertIn("osasco", notes, msg=notes)
        self.assertNotIn("solução solicitada", notes, msg=notes)
        self.assertNotIn("ja falei", notes, msg=notes)
        self.assertNotIn("|", notes, msg=notes)

        final_reply = last_response.json()["reply"].lower()
        self.assertFalse(final_reply.startswith("olá"), msg=final_reply)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_joaquim_frigorifica_flow_builds_structured_technical_notes(self):
        mail.outbox.clear()
        session_key = "real-flow-joaquim-frigorifica"
        url = reverse("livia_assistant:chat")
        flow = [
            "estou com problemas em um equipamennto que parou",
            "uma camara frigorifica",
            "Joaquim",
            "Animalia",
            "Cotia",
            "11962196100",
            "anamalia@animalia.com.br",
        ]
        last_response = None
        for message in flow:
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )

        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertTrue(capture.is_qualified)
        self.assertEqual(capture.operational_status, LiviaLeadCapture.OperationalStatus.SENT_TO_CRM)
        self.assertEqual(len(mail.outbox), 1)

        notes = capture.notes or ""
        notes_lower = notes.lower()
        self.assertIn("câmara frigorífica", notes_lower, msg=notes)
        self.assertTrue("parada" in notes_lower or "parou" in notes_lower, msg=notes)
        self.assertIn("cotia", notes_lower, msg=notes)
        self.assertNotIn("equipamennto", notes_lower, msg=notes)
        self.assertNotIn("|", notes, msg=notes)
        self.assertIn(notes_lower, mail.outbox[0].body.lower())

        history = (capture.crm_reference or {}).get("technical_history", [])
        self.assertTrue(any("camara frigorifica" in item.lower() for item in history))
        self.assertTrue(last_response.json()["lead_registered"])

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_registered_lead_keeps_same_capture_for_new_air_conditioner_e2_question(self):
        mail.outbox.clear()
        session_key = "isolation-duno-to-air-conditioner-e2"
        url = reverse("livia_assistant:chat")

        first_cycle = [
            "quero um robô Duno para limpeza em supermercado",
            "quero atendimento",
            "Marcelo",
            "Smart Control",
            "Osasco",
            "11999999999",
            "marcelo@teste.com",
        ]
        for message in first_cycle:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        first_lead = (
            LiviaLeadCapture.objects.filter(conversation__session_key=session_key)
            .order_by("created_at", "id")
            .first()
        )
        self.assertIsNotNone(first_lead)
        captures = list(LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("created_at", "id"))
        print(f"DEBUG: lead_count={len(captures)}")
        for cap in captures:
            print(f"DEBUG CAPTURE: id={cap.id}, name={cap.name}, company={cap.company}, city={cap.city}, phone={cap.phone}, email={cap.email}, notes={cap.notes}, interest={cap.service_interest}, qualified={cap.is_qualified}")
        self.assertTrue(first_lead.is_qualified)
        self.assertEqual(first_lead.operational_status, LiviaLeadCapture.OperationalStatus.SENT_TO_CRM)

        last_reply = ""
        second_cycle = [
            "estou com problema em um ar condicionado",
            "erro E2",
            "quero atendimento",
            "11987654321",
            "Digitalcold1@gmail.com",
        ]
        for message in second_cycle:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            last_reply = response.json()["reply"].lower()

        captures = list(
            LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("created_at", "id")
        )
        self.assertEqual(len(captures), 2)
        first_lead, new_lead = captures

        self.assertTrue(first_lead.is_qualified)
        self.assertEqual(first_lead.operational_status, LiviaLeadCapture.OperationalStatus.SENT_TO_CRM)
        self.assertEqual((first_lead.name or "").lower(), "marcelo")
        self.assertFalse(new_lead.is_qualified)

        notes = (first_lead.notes or first_lead.service_interest or "").lower()
        self.assertIn("duno", notes)
        history = " ".join((new_lead.crm_reference or {}).get("technical_history", [])).lower()
        self.assertTrue("ar condicionado" in history or "ar-condicionado" in history, msg=history)
        self.assertIn("e2", history)
        self.assertFalse(last_reply.startswith("olá"), msg=last_reply)
        self.assertFalse(response.json()["lead_registered"])
        self.assertNotIn("vou encaminhar", last_reply)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_notified_conversation_new_logistics_subject_appends_without_duplicate_email(self):
        """Teste A: lead já notificado + novo assunto logístico não duplica e-mail nem diz 'já encaminhei'."""
        mail.outbox.clear()
        session_key = "test-a-logistics-after-notified"
        url = reverse("livia_assistant:chat")

        first_cycle = [
            "quero orçamento para um sistema web com IA",
            "Marcelo",
            "Smart Control",
            "São Paulo",
            "11999999999",
            "marcelo@smartcontrol.com.br",
        ]
        for message in first_cycle:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        first_lead = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).first()
        self.assertTrue(first_lead.is_qualified)
        self.assertIn("notification_sent_at", first_lead.crm_reference)
        self.assertEqual(len(mail.outbox), 1)
        first_lead.refresh_from_db()
        service = LiviaAssistantService()
        self.assertIsNotNone(
            service.get_locked_lead_capture(first_lead.conversation),
            msg=first_lead.crm_reference,
        )
        self.assertTrue(is_lead_ready_for_notification(first_lead))
        self.assertTrue(service._conversation_was_notified(first_lead.conversation))
        self.assertEqual(LiviaConversation.objects.filter(session_key=session_key).count(), 1)
        self.assertTrue(
            service.is_new_commercial_cycle_message(
                "quero orçamento para um sistema logístico web com IA para entregas",
                first_lead.conversation,
            )
        )

        followup = self.client.post(
            url,
            data=json.dumps(
                {
                    "message": (
                        "quero orçamento para um sistema logístico web com IA para entregas agendadas, "
                        "rotas, frota e fretes em todo o Brasil"
                    ),
                    "session_key": session_key,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(followup.status_code, 200)
        reply = followup.json()["reply"].lower()
        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse(followup.json()["lead_registered"])
        self.assertTrue(followup.json()["lead_detected"])
        self.assertEqual(LiviaLeadCapture.objects.filter(conversation__session_key=session_key).count(), 2)
        self.assertNotIn("vou encaminhar", reply)
        self.assertNotIn("já encaminhei", reply)
        self.assertNotIn("enviei", reply)
        self.assertIn("como posso te chamar", reply)
        self.assertNotIn("já temos seus dados", reply)
        self.assertFalse(
            reply.strip()
            == "já temos seus dados registrados. vou acrescentar essa informação ao atendimento.",
            msg=reply,
        )

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_notified_conversation_generic_system_need_continues_discovery(self):
        mail.outbox.clear()
        session_key = "test-notified-generic-system-discovery"
        url = reverse("livia_assistant:chat")
        first_cycle = [
            "quero orçamento para um sistema web com IA",
            "Marcelo",
            "Smart Control",
            "São Paulo",
            "11999999999",
            "marcelo@smartcontrol.com.br",
        ]
        for message in first_cycle:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        self.assertEqual(len(mail.outbox), 1)

        followup = self.client.post(
            url,
            data=json.dumps({"message": "ola preciso de um sistema", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(followup.status_code, 200)
        payload = followup.json()
        reply = payload["reply"].lower()
        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse(payload["lead_registered"])
        self.assertTrue(
            any(term in reply for term in ("tipo de sistema", "controle interno", "estoque", "vendas", "entregas")),
            msg=reply,
        )
        self.assertFalse(
            reply.strip()
            == "já temos seus dados registrados. vou acrescentar essa informação ao atendimento.",
            msg=reply,
        )

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_notified_conversation_food_delivery_continues_discovery(self):
        mail.outbox.clear()
        session_key = "test-notified-food-delivery-discovery"
        url = reverse("livia_assistant:chat")
        first_cycle = [
            "quero orçamento para um sistema web com IA",
            "Marcelo",
            "Smart Control",
            "São Paulo",
            "11999999999",
            "marcelo@smartcontrol.com.br",
        ]
        for message in first_cycle:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        self.assertEqual(len(mail.outbox), 1)

        followup = self.client.post(
            url,
            data=json.dumps(
                {"message": "preciso de um sistema de entrega de alimentos", "session_key": session_key}
            ),
            content_type="application/json",
        )
        self.assertEqual(followup.status_code, 200)
        payload = followup.json()
        reply = payload["reply"].lower()
        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse(payload["lead_registered"])
        self.assertTrue(
            any(
                term in reply
                for term in ("entrega", "alimentos", "pedidos", "entregadores", "estabelecimentos", "painel")
            ),
            msg=reply,
        )
        self.assertFalse(
            reply.strip()
            == "já temos seus dados registrados. vou acrescentar essa informação ao atendimento.",
            msg=reply,
        )

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_notified_conversation_web_capability_question_gets_clear_answer(self):
        mail.outbox.clear()
        session_key = "test-notified-web-capability"
        url = reverse("livia_assistant:chat")
        first_cycle = [
            "quero orçamento para um sistema web com IA",
            "Marcelo",
            "Smart Control",
            "São Paulo",
            "11999999999",
            "marcelo@smartcontrol.com.br",
        ]
        for message in first_cycle:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        self.client.post(
            url,
            data=json.dumps(
                {"message": "preciso de um sistema de entrega de alimentos", "session_key": session_key}
            ),
            content_type="application/json",
        )
        self.assertEqual(len(mail.outbox), 1)

        followup = self.client.post(
            url,
            data=json.dumps({"message": "voces fazem sistemas web?", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(followup.status_code, 200)
        payload = followup.json()
        reply = payload["reply"].lower()
        self.assertEqual(len(mail.outbox), 1)
        self.assertFalse(payload["lead_registered"])
        self.assertIn("sim", reply)
        self.assertTrue(
            any(term in reply for term in ("sistemas web", "painéis", "paineis", "portais", "gestão", "gestao")),
            msg=reply,
        )
        self.assertFalse(
            reply.strip()
            == "já temos seus dados registrados. vou acrescentar essa informação ao atendimento.",
            msg=reply,
        )

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_logistics_web_system_flow_summary_not_consulting_ia(self):
        """Teste B: fluxo logístico web mantém interesse correto no resumo."""
        mail.outbox.clear()
        session_key = "test-b-logistics-web-flow"
        url = reverse("livia_assistant:chat")
        flow = [
            "quero orçamento para um sistema web com IA integrada",
            "preciso de um sistema logístico para entregas",
            "o SaaS atual será perdido e preciso de sistema novo",
            "gestão operacional com entregas agendadas e on demand",
            "rodar no Brasil todo",
            "Marcelo",
            "LogBrasil",
            "São Paulo",
            "11988887777",
            "marcelo@logbrasil.com.br",
        ]
        last_response = None
        for message in flow:
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(last_response.status_code, 200)

        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertTrue(capture.is_qualified)
        summary = (capture.notes or "").lower()
        interest = (capture.service_interest or "").lower()
        self.assertTrue(
            "sistema logístico web" in summary or "sistema logístico" in summary or "sistema web" in summary,
            msg=summary,
        )
        self.assertTrue(
            any(term in summary for term in ("entregas", "rotas", "fretes", "frota", "motoristas")),
            msg=summary,
        )
        self.assertNotIn("consultoria em inteligência artificial", summary)
        self.assertNotIn("consultoria em inteligencia artificial", summary)
        self.assertNotIn("consultoria", interest)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("vou encaminhar", last_response.json()["reply"].lower())

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_fresh_conversation_sends_single_notification_and_confirms_forwarding(self):
        """Teste D: conversa nova completa envia notificação uma vez e confirma encaminhamento."""
        mail.outbox.clear()
        session_key = "test-d-fresh-notification"
        url = reverse("livia_assistant:chat")
        flow = [
            "quero orçamento para desenvolvimento de sistema web",
            "Ana",
            "Empresa Beta",
            "Campinas",
            "11977776666",
            "ana@empresa.com.br",
        ]
        last_response = None
        for message in flow:
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(last_response.status_code, 200)

        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(last_response.json()["lead_registered"])
        reply = last_response.json()["reply"].lower()
        self.assertIn("vou encaminhar", reply)
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).first()
        self.assertTrue((capture.crm_reference or {}).get("notification_sent_this_turn"))
        self.assertIn("notification_sent_at", capture.crm_reference)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_air_conditioner_e2_full_flow_qualifies_without_duno_contamination(self):
        mail.outbox.clear()
        session_key = "air-conditioner-e2-full-flow"
        url = reverse("livia_assistant:chat")

        flow = [
            "estou com problema em um ar condicionado",
            "erro E2",
            "quero atendimento",
            "João",
            "Digital Cold",
            "Cotia",
            "11987654321",
            "joao@digitalcold.com.br",
        ]
        last_response = None
        for message in flow:
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(last_response.status_code, 200)

        capture = (
            LiviaLeadCapture.objects.filter(conversation__session_key=session_key)
            .order_by("-created_at", "-id")
            .first()
        )
        self.assertIsNotNone(capture)
        self.assertTrue(capture.is_qualified)
        self.assertEqual(capture.operational_status, LiviaLeadCapture.OperationalStatus.SENT_TO_CRM)
        self.assertEqual(capture.name.lower(), "joão")
        self.assertEqual(capture.company.lower(), "digital cold")
        self.assertEqual(capture.city.lower(), "cotia")

        notes = (capture.notes or capture.service_interest or "").lower()
        history = " ".join((capture.crm_reference or {}).get("technical_history", [])).lower()
        self.assertTrue("ar condicionado" in history or "ar-condicionado" in history, msg=history)
        self.assertIn("e2", history)
        self.assertNotIn("duno", notes)
        self.assertTrue(last_response.json()["lead_registered"])

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_food_delivery_pizzaria_rich_context_continues_discovery_before_lead_collection(self):
        """Discovery digital: contexto rico de pizzaria não deve iniciar coleta de contato cedo."""
        mail.outbox.clear()
        session_key = "food-delivery-pizzaria-discovery"
        url = reverse("livia_assistant:chat")
        flow = [
            "voces trabalham com aplicativos moveis",
            "quero um sistema de entrega de comida",
            (
                "tenho uma pequena rede de pizzarias e gostaria de ter entrega automatizada, "
                "bem como cardapio no tablet"
            ),
        ]
        last_response = None
        for message in flow:
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(last_response.status_code, 200)

        reply = last_response.json()["reply"].lower()
        self.assertNotIn("como posso te chamar", reply)
        self.assertNotIn("telefone/whatsapp", reply)
        self.assertNotIn("e-mail", reply)
        self.assertTrue(
            any(
                term in reply
                for term in (
                    "entregador",
                    "pagamento",
                    "app",
                    "site",
                    "tablet",
                    "unidades",
                    "lojas",
                    "painel",
                )
            ),
            msg=reply,
        )
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(last_response.json()["lead_registered"])

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_explicit_budget_for_delivery_app_starts_lead_collection(self):
        session_key = "explicit-budget-delivery-app"
        url = reverse("livia_assistant:chat")
        response = self.client.post(
            url,
            data=json.dumps(
                {
                    "message": "quero orçamento para um app de delivery para minha pizzaria",
                    "session_key": session_key,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        reply = response.json()["reply"].lower()
        self.assertIn("como posso te chamar", reply)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_spontaneous_phone_during_food_delivery_discovery_is_saved_without_notification(self):
        mail.outbox.clear()
        session_key = "food-delivery-spontaneous-phone"
        url = reverse("livia_assistant:chat")

        for message in (
            "voces trabalham com aplicativos moveis",
            "quero um sistema de entrega de comida",
        ):
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)

        phone_response = self.client.post(
            url,
            data=json.dumps({"message": "11988887766", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(phone_response.status_code, 200)
        self.assertFalse(phone_response.json()["lead_registered"])
        self.assertEqual(len(mail.outbox), 0)

        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).first()
        self.assertIsNotNone(capture)
        self.assertEqual(capture.phone, "11988887766")
        self.assertFalse(capture.is_qualified)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_food_delivery_discovery_handoff_after_minimum_context(self):
        mail.outbox.clear()
        session_key = "food-delivery-discovery-handoff"
        url = reverse("livia_assistant:chat")
        flow = [
            "voces trabalham com aplicativos moveis",
            "quero um sistema de entrega de comida",
            (
                "tenho uma pequena rede de pizzarias e gostaria de ter entrega automatizada, "
                "bem como cardapio no tablet"
            ),
            "entregadores proprios",
            "preciso de pagamento online com pix e cartao",
            "sao 3 lojas na primeira fase",
            "sim, preciso de painel administrativo com cardapio e status dos pedidos",
        ]
        replies = []
        for message in flow:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            replies.append(response.json()["reply"].lower())

        handoff_replies = [
            reply
            for reply in replies
            if "registrar seu atendimento" in reply or "bom ponto de partida" in reply
        ]
        self.assertTrue(handoff_replies, msg=replies)
        self.assertTrue(any("como posso te chamar" in reply for reply in handoff_replies))
        self.assertTrue(
            any("pizzaria" in reply or "delivery" in reply or "cardápio" in reply or "cardapio" in reply for reply in handoff_replies),
            msg=handoff_replies,
        )
        self.assertNotIn("solução solicitada", " ".join(handoff_replies))


    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_notified_previous_lead_does_not_block_new_marmoraria_cycle(self):
        mail.outbox.clear()
        session_key = "marmoraria-new-cycle-after-old-lead"
        url = reverse("livia_assistant:chat")

        first_cycle = [
            "quero orçamento para um sistema para meu depósito",
            "Ed",
            "Depósito Ed",
            "São Paulo",
            "11911112222",
            "ed@ed.com",
        ]
        for message in first_cycle:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        start = self.client.post(
            url,
            data=json.dumps({
                "message": "boa noite vi uma postagem no facebook e estou interessado em criar um sistema para minha marmoraria",
                "session_key": session_key,
            }),
            content_type="application/json",
        )
        self.assertEqual(start.status_code, 200)
        start_reply = start.json()["reply"].lower()
        self.assertNotIn("como já temos seus dados", start_reply)
        self.assertNotIn("já temos seus dados registrados", start_reply)
        self.assertFalse(start.json()["lead_registered"])

        flow = ["Antonio", "1145454545", "antonio@marmore.com.br", "Osasco"]
        last_response = None
        for message in flow:
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(last_response.status_code, 200)

        captures = list(LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("created_at", "id"))
        self.assertEqual(len(mail.outbox), 2)
        self.assertTrue(last_response.json()["lead_registered"])
        self.assertEqual(len(captures), 2)
        first_lead, second_lead = captures
        self.assertEqual(first_lead.email, "ed@ed.com")
        self.assertEqual(second_lead.name, "Antonio")
        self.assertEqual(second_lead.email, "antonio@marmore.com.br")
        self.assertEqual(second_lead.phone, "1145454545")
        self.assertEqual(second_lead.city, "Osasco")
        self.assertTrue((second_lead.crm_reference or {}).get("notification_sent_this_turn"))
        second_body = mail.outbox[-1].body.lower()
        self.assertIn("antonio@marmore.com.br", second_body)
        self.assertIn("marmoraria", second_body)
        self.assertNotIn("ed@ed.com", second_body)
        self.assertNotIn("depósito ed", second_body)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_same_cycle_followup_after_notification_does_not_send_duplicate_email(self):
        mail.outbox.clear()
        session_key = "same-cycle-followup-no-duplicate"
        url = reverse("livia_assistant:chat")
        flow = [
            "quero orçamento para um sistema para minha marmoraria",
            "Antonio",
            "1145454545",
            "antonio@marmore.com.br",
            "Osasco",
        ]
        last_response = None
        for message in flow:
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(last_response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(last_response.json()["lead_registered"])

        followup = self.client.post(
            url,
            data=json.dumps({"message": "também preciso controlar chapas e orçamento por metro", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(followup.status_code, 200)
        self.assertFalse(followup.json()["lead_registered"])
        self.assertEqual(len(mail.outbox), 1)
        captures = LiviaLeadCapture.objects.filter(conversation__session_key=session_key)
        self.assertEqual(captures.count(), 1)
        history = " ".join((captures.first().crm_reference or {}).get("technical_history", [])).lower()
        self.assertIn("chapas", history)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_closed_cycle_allows_new_commercial_cycle(self):
        mail.outbox.clear()
        session_key = "closed-cycle-allows-new-lead"
        url = reverse("livia_assistant:chat")
        first_cycle = [
            "quero orçamento para um sistema para meu depósito",
            "Ed",
            "Depósito Ed",
            "São Paulo",
            "11911112222",
            "ed@ed.com",
        ]
        for message in first_cycle:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        close = self.client.post(
            url,
            data=json.dumps({"message": "por hora é só", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(close.status_code, 200)

        second_cycle = [
            "agora quero orçamento para um sistema para minha marmoraria",
            "Antonio",
            "1145454545",
            "antonio@marmore.com.br",
            "Osasco",
        ]
        last_response = None
        for message in second_cycle:
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(last_response.status_code, 200)
        self.assertEqual(len(mail.outbox), 2)
        self.assertTrue(last_response.json()["lead_registered"])


class LeadCycleFieldCorrectionViewTests(TestCase):
    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_new_cycle_after_lorena_does_not_greet_with_old_name(self):
        mail.outbox.clear()
        session_key = "new-cycle-no-lorena-leak"
        url = reverse("livia_assistant:chat")
        lorena_cycle = [
            "quero orçamento para um sistema web",
            "Lorena",
            "Empresa Lorena",
            "Campinas",
            "11988887777",
            "lorena@old.com",
        ]
        for message in lorena_cycle:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)

        new_cycle = self.client.post(
            url,
            data=json.dumps(
                {
                    "message": "agora quero um app para artesanato e transformar fotos em arte",
                    "session_key": session_key,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(new_cycle.status_code, 200)
        reply = new_cycle.json()["reply"].lower()
        self.assertNotIn("lorena", reply)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_name_correction_message_clears_old_name_without_city_side_effect(self):
        mail.outbox.clear()
        session_key = "name-correction-view"
        url = reverse("livia_assistant:chat")
        for message in [
            "quero um app para artesanato",
            "Lorena",
            "Empresa Teste",
            "Campinas",
        ]:
            self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
        correction = self.client.post(
            url,
            data=json.dumps(
                {
                    "message": "celular, mas Livia eu não sou a Lorena nem conheço e ainda não te falei meu nome",
                    "session_key": session_key,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(correction.status_code, 200)
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertNotEqual((capture.name or "").lower(), "lorena")
        self.assertNotEqual((capture.city or "").lower(), "celular")

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_discovery_celular_answer_does_not_persist_as_city(self):
        mail.outbox.clear()
        session_key = "discovery-celular-not-city"
        url = reverse("livia_assistant:chat")
        self.client.post(
            url,
            data=json.dumps({"message": "quero um app para artesanato", "session_key": session_key}),
            content_type="application/json",
        )
        self.client.post(
            url,
            data=json.dumps({"message": "transformar foto em arte", "session_key": session_key}),
            content_type="application/json",
        )
        self.client.post(
            url,
            data=json.dumps({"message": "celular", "session_key": session_key}),
            content_type="application/json",
        )
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        if capture is not None:
            self.assertNotEqual((capture.city or "").lower(), "celular")
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_after_company_collection_asks_phone_not_discovery(self):
        mail.outbox.clear()
        session_key = "cassia-company-then-phone"
        url = reverse("livia_assistant:chat")
        flow = [
            "quero orçamento para um app de artesanato para transformar fotos em arte",
            "cadastro de clientes",
            "Cassia",
        ]
        for message in flow:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
        company_response = self.client.post(
            url,
            data=json.dumps({"message": "cassia dag", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(company_response.status_code, 200)
        reply = company_response.json()["reply"].lower()
        self.assertTrue(
            any(term in reply for term in ("telefone", "whatsapp")),
            msg=reply,
        )
        self.assertNotIn("que tipo de sistema", reply)

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_cassia_artesanato_flow_registers_once_with_specific_summary(self):
        mail.outbox.clear()
        session_key = "cassia-artesanato-full-flow"
        url = reverse("livia_assistant:chat")
        flow = [
            "quero orçamento para um app de artesanato para transformar fotos em arte",
            "cadastro de clientes",
            "celular",
            "Cassia",
            "cassia dag",
            "11977776666",
            "cassia@artesanato.com.br",
            "Sorocaba",
        ]
        last_response = None
        for message in flow:
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(last_response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(last_response.json()["lead_registered"])
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertEqual(capture.name.lower(), "cassia")
        self.assertEqual(capture.company.lower(), "cassia dag")
        self.assertEqual(capture.city.lower(), "sorocaba")
        self.assertNotIn("lorena", (capture.name or "").lower())
        body = mail.outbox[0].body.lower()
        self.assertTrue(any(term in body for term in ("artesanato", "arte", "foto", "fotos")))
        self.assertTrue(any(term in body for term in ("clientes", "cadastro")))
        self.assertNotEqual((capture.city or "").lower(), "celular")

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_geraldo_marmoraria_flow_rejects_long_phrase_as_city(self):
        mail.outbox.clear()
        session_key = "geraldo-marmoraria-full-flow"
        url = reverse("livia_assistant:chat")
        flow = [
            "quero orçamento para um sistema para minha marmoraria",
            "controle de estoque clientes vendas e captação de contatos",
            "faço tudo em caderno de anotação as vezes acho que to na idade da pedra",
            "Geraldo",
            "11966665555",
            "geraldo@marmoraria.com.br",
            "Campinas",
        ]
        last_response = None
        for message in flow:
            last_response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(last_response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(last_response.json()["lead_registered"])
        capture = LiviaLeadCapture.objects.filter(conversation__session_key=session_key).order_by("-created_at").first()
        self.assertEqual(capture.name.lower(), "geraldo")
        self.assertEqual(capture.city.lower(), "campinas")
        self.assertNotIn("caderno", (capture.city or "").lower())
        self.assertNotIn("idade da pedra", (capture.city or "").lower())
        body = mail.outbox[0].body.lower()
        self.assertIn("marmoraria", body)
        self.assertTrue(any(term in body for term in ("estoque", "clientes", "vendas", "captação", "captacao")))

    @override_settings(LIVIA_AI_PROVIDER="fallback")
    def test_livia_does_not_recollect_data_after_qualified_lead_on_short_confirmation(self):
        mail.outbox.clear()
        session_key = "test-post-lead-protection"
        url = reverse("livia_assistant:chat")
        
        # 1-3. Usuário pede orçamento e Lívia qualifica o lead
        flow = [
            "quero orçamento para robô",
            "Ricardo",
            "ABB",
            "1123232323",
            "dadoi@dodoi.com.br",
            "são paulo",
        ]
        
        for message in flow:
            response = self.client.post(
                url,
                data=json.dumps({"message": message, "session_key": session_key}),
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200)
            
        self.assertTrue(response.json()["lead_registered"])
        
        # 4. Usuário pergunta sobre assistência técnica
        response = self.client.post(
            url,
            data=json.dumps({"message": "como funciona a assistência técnica?", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        
        # 6. Usuário responde: "sim gostaria"
        response = self.client.post(
            url,
            data=json.dumps({"message": "sim gostaria", "session_key": session_key}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        
        # 7. Validar que a resposta NÃO pede dados comerciais
        reply = response.json()["reply"].lower()
        self.assertNotIn("empresa e telefone", reply)
        self.assertNotIn("qual sua empresa", reply)
        self.assertNotIn("qual telefone", reply)
        self.assertNotIn("e-mail", reply)
        self.assertNotIn("como posso te chamar", reply)
        
        # 8. Validar que a resposta contém complemento
        self.assertIn("complemento", reply)

