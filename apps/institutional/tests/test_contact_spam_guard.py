from django.test import SimpleTestCase

from apps.institutional.services.contact_spam_guard import (
    ContactSubmissionClass,
    classify_contact_submission,
    is_contact_rate_limited,
)


class ContactSpamGuardTests(SimpleTestCase):
    def test_ken_carrell_example_is_spam(self):
        verdict = classify_contact_submission(
            {
                "contact_name": "Ken Carrell",
                "company": "Ken",
                "whatsapp": "737550229",
                "email": "kenp2025x@yahoo.com",
                "interest": "software",
                "message": (
                    "Was just browsing smartcontrolbrasil.com.br and was impressed the layout. "
                    "Nicely design and great user experience. Just had to drop a message, "
                    "have a great day! we7f8sd82"
                ),
            }
        )

        self.assertEqual(verdict.classification, ContactSubmissionClass.SPAM)
        self.assertGreaterEqual(verdict.score, 45)

    def test_legitimate_portuguese_submission_is_clean(self):
        verdict = classify_contact_submission(
            {
                "contact_name": "Maria Silva",
                "company": "Indústria Exemplo",
                "whatsapp": "(11) 99999-9999",
                "email": "maria@example.com",
                "interest": "automacao",
                "main_problem": "Automatizar linha de produção",
                "message": "Precisamos avaliar escopo, prazo e orçamento para integração de CLP.",
            }
        )

        self.assertEqual(verdict.classification, ContactSubmissionClass.CLEAN)

    def test_legitimate_english_submission_is_clean(self):
        verdict = classify_contact_submission(
            {
                "contact_name": "John Smith",
                "company": "Acme Packaging Ltd",
                "whatsapp": "+1 555 123 4567",
                "email": "john@gmail.com",
                "interest": "automacao",
                "message": (
                    "We need PLC integration for our packaging line. "
                    "Please send a quote and estimated timeline."
                ),
            }
        )

        self.assertEqual(verdict.classification, ContactSubmissionClass.CLEAN)

    def test_honeypot_is_spam(self):
        verdict = classify_contact_submission(
            {
                "contact_name": "Bot",
                "email": "bot@example.com",
                "message": "Mensagem longa o suficiente para passar no mínimo.",
                "website": "https://spam.example",
            }
        )

        self.assertEqual(verdict.classification, ContactSubmissionClass.SPAM)
        self.assertIn("honeypot_filled", verdict.reasons)


class ContactRateLimitTests(SimpleTestCase):
    def test_rate_limit_blocks_after_threshold(self):
        from django.core.cache import cache

        cache.clear()
        ip = "203.0.113.10"

        self.assertFalse(is_contact_rate_limited(ip, limit=2, window_seconds=60))
        self.assertFalse(is_contact_rate_limited(ip, limit=2, window_seconds=60))
        self.assertTrue(is_contact_rate_limited(ip, limit=2, window_seconds=60))
