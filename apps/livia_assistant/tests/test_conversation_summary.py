from django.core import mail
from django.test import TestCase

from apps.livia_assistant.conversation_summary import (
    build_conversation_summary,
    build_conversation_transcript,
    build_lead_notification_body,
)
from apps.livia_assistant.crm_bridge import LiviaCRMBridge
from apps.livia_assistant.models import LiviaConversation, LiviaLeadCapture, LiviaMessage


class ConversationSummaryTests(TestCase):
    def setUp(self):
        self.conversation = LiviaConversation.objects.create(session_key="summary-session", source_page="/contato")
        self.lead = LiviaLeadCapture.objects.create(
            conversation=self.conversation,
            name="Marcos",
            email="marcos@example.com",
            phone="11999990000",
            company="Govip",
            city="São Paulo",
            service_interest="desenvolvimento de sistema logístico web com IA integrada",
            notes="Cliente interessado em desenvolvimento de sistema logístico web próprio com IA integrada.",
            is_qualified=True,
            crm_reference={
                "technical_history": [
                    "quero orçamento para um sistema logístico web com IA",
                    "preciso de entregas agendadas, rotas e gestão de frota",
                ],
                "category": "sistemas_web_ia",
            },
        )
        first_message = LiviaMessage.objects.create(
            conversation=self.conversation,
            role=LiviaMessage.Role.USER,
            content="quero orçamento para um sistema logístico web com IA",
        )
        self.lead.crm_reference["capture_start_message_id"] = first_message.id
        self.lead.save(update_fields=["crm_reference"])
        remaining_messages = [
            ("assistant", "Para orçamento, primeiro alinhamos escopo técnico."),
            ("user", "preciso de entregas agendadas, rotas e gestão de frota"),
            ("assistant", "Entendi. Como posso te chamar?"),
            ("user", "Marcos"),
            ("user", "Govip"),
            ("user", "São Paulo"),
            ("user", "11999990000"),
            ("user", "marcos@example.com"),
        ]
        for role, content in remaining_messages:
            LiviaMessage.objects.create(
                conversation=self.conversation,
                role=role,
                content=content,
            )

    def test_build_conversation_summary_includes_structured_sections(self):
        summary = build_conversation_summary(self.conversation, lead=self.lead)

        self.assertTrue(summary.executive_summary)
        self.assertIn("logístico", summary.main_need.lower())
        self.assertGreaterEqual(len(summary.key_points), 2)
        self.assertIn("Urgência:", summary.suggested_classification)
        self.assertTrue(summary.recommended_next_action)

    def test_build_conversation_transcript_includes_client_and_livia_turns(self):
        transcript = build_conversation_transcript(self.conversation, lead=self.lead)

        self.assertIn("Cliente: quero orçamento para um sistema logístico web com IA", transcript)
        self.assertIn("Lívia: Para orçamento, primeiro alinhamos escopo técnico.", transcript)
        self.assertIn("Cliente: preciso de entregas agendadas, rotas e gestão de frota", transcript)

    def test_build_conversation_transcript_excludes_system_messages(self):
        LiviaMessage.objects.create(
            conversation=self.conversation,
            role=LiviaMessage.Role.SYSTEM,
            content="prompt interno com token: abcdef123456",
        )
        transcript = build_conversation_transcript(self.conversation, lead=self.lead)

        self.assertNotIn("prompt interno", transcript.lower())
        self.assertNotIn("token:", transcript.lower())

    def test_build_lead_notification_body_contains_summary_and_transcript(self):
        body = build_lead_notification_body(self.lead, timestamp="16/06/2026 10:30")

        self.assertIn("Resumo executivo:", body)
        self.assertIn("Necessidade principal:", body)
        self.assertIn("Pontos importantes levantados:", body)
        self.assertIn("Classificação sugerida:", body)
        self.assertIn("Próxima ação recomendada:", body)
        self.assertIn("Histórico da conversa:", body)
        self.assertIn("Cliente: quero orçamento para um sistema logístico web com IA", body)


class ConversationSummaryEmailIntegrationTests(TestCase):
    def setUp(self):
        mail.outbox.clear()
        self.conversation = LiviaConversation.objects.create(session_key="email-summary-session")
        self.lead = LiviaLeadCapture.objects.create(
            conversation=self.conversation,
            name="Cliente Teste",
            email="cliente@example.com",
            phone="11999999999",
            company="Empresa Teste",
            city="São Paulo",
            service_interest="PMOC",
            urgency=LiviaLeadCapture.Urgency.HIGH,
            notes="quero orçamento de PMOC para câmara frigorífica",
            is_qualified=True,
            crm_reference={"capture_start_message_id": None},
        )
        first_message = LiviaMessage.objects.create(
            conversation=self.conversation,
            role=LiviaMessage.Role.USER,
            content="preciso de PMOC para câmara frigorífica com acúmulo de gelo",
        )
        self.lead.crm_reference["capture_start_message_id"] = first_message.id
        self.lead.save(update_fields=["crm_reference"])
        LiviaMessage.objects.create(
            conversation=self.conversation,
            role=LiviaMessage.Role.ASSISTANT,
            content="Posso te ajudar com diagnóstico e manutenção preventiva.",
        )
        LiviaMessage.objects.create(
            conversation=self.conversation,
            role=LiviaMessage.Role.USER,
            content="quero orçamento e visita técnica em São Paulo",
        )

    def test_notification_email_contains_conversation_summary_and_transcript(self):
        with self.settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            LiviaCRMBridge().create_or_update_crm_lead(self.lead)

        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertIn("Nome: Cliente Teste", body)
        self.assertIn("Empresa: Empresa Teste", body)
        self.assertIn("Telefone/WhatsApp: 11999999999", body)
        self.assertIn("E-mail: cliente@example.com", body)
        self.assertIn("Resumo executivo:", body)
        self.assertIn("Histórico da conversa:", body)
        self.assertIn("Cliente: preciso de PMOC para câmara frigorífica com acúmulo de gelo", body)

    def test_notification_is_not_duplicated_for_already_notified_conversation(self):
        with self.settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            LiviaCRMBridge().create_or_update_crm_lead(self.lead)
            second_capture = LiviaLeadCapture.objects.create(
                conversation=self.conversation,
                name="Cliente Teste 2",
                email="cliente2@example.com",
                phone="11999999998",
                company="Empresa Teste",
                city="São Paulo",
                service_interest="PMOC",
                notes="novo contato na mesma conversa",
                is_qualified=True,
            )
            LiviaCRMBridge().create_or_update_crm_lead(second_capture)

        self.assertEqual(len(mail.outbox), 1)
