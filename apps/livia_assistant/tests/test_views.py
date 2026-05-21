import json
import os
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.livia_assistant.models import LiviaConversation, LiviaLeadCapture, LiviaMessage


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
                    "message": "Tenho uma máquina parada e preciso de ajuda urgente",
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
