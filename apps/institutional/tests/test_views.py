from django.conf import settings
from django.core import mail
from django.test import SimpleTestCase, override_settings
from django.urls import reverse


TEST_MIDDLEWARE = [
    mw
    for mw in settings.MIDDLEWARE
    if mw != "shared_kernel.observability.middleware.CorrelationIdMiddleware"
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class InstitutionalRoutesTests(SimpleTestCase):
    # Middleware de observabilidade grava traces no banco durante requests ao client.
    databases = {"default"}
    def test_public_pages_render(self):
        route_names = [
            "institutional:home",
            "institutional:about",
            "institutional:services",
            "institutional:blog",
            "institutional:contact",
            "institutional:refrigeracao",
            "institutional:representada_mitsubishi_automacao",
            "institutional:service_manutencao_tpm_confiabilidade",
            "institutional:service_automacao_industrial_clps",
            "institutional:service_robotica_integracao",
            "institutional:parceiro_xyron_robotics",
            "institutional:seguranca_da_informacao",
            "institutional:sites_sistemas_marketing",
        ]

        for route_name in route_names:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)

    def test_xyron_robotics_page_uses_partner_template(self):
        response = self.client.get(reverse("institutional:parceiro_xyron_robotics"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "institutional/eitech/pages/xyron-robotics.html"
        )

    def test_services_canonical_url_is_solucoes(self):
        self.assertEqual(reverse("institutional:services"), "/solucoes/")

    def test_legacy_servicos_redirects_permanently_to_solucoes(self):
        rsp = self.client.get("/servicos/", follow=False)
        self.assertRedirects(
            rsp,
            reverse("institutional:services"),
            status_code=301,
            fetch_redirect_response=False,
        )


@override_settings(
    MIDDLEWARE=TEST_MIDDLEWARE,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CONTACT_FORM_RECIPIENTS=["contato@smartcontrolbrasil.com.br"],
    CONTACT_FORM_BCC=["engenharia@smartcontrolbrasil.com.br"],
)
class ContactViewTests(SimpleTestCase):
    databases = {"default"}

    def setUp(self):
        mail.outbox.clear()
        self.url = reverse("institutional:contact")
        self.valid_data = {
            "contact_name": "Maria Silva",
            "company": "Indústria Exemplo",
            "whatsapp": "(11) 99999-9999",
            "email": "maria@example.com",
            "segment": "Indústria",
            "interest": "automacao",
            "main_problem": "Automatizar uma linha de produção",
            "message": "Precisamos avaliar escopo e prazo.",
        }

    def test_contact_get_returns_200(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)

    def test_valid_post_sends_email_and_redirects(self):
        response = self.client.post(self.url, self.valid_data)

        self.assertRedirects(
            response,
            self.url,
            fetch_redirect_response=False,
        )
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(
            sent_email.to,
            ["contato@smartcontrolbrasil.com.br"],
        )
        self.assertEqual(sent_email.bcc, ["engenharia@smartcontrolbrasil.com.br"])
        self.assertEqual(sent_email.reply_to, ["maria@example.com"])
        self.assertIn("Nome: Maria Silva", sent_email.body)
        self.assertIn("Mensagem:\nPrecisamos avaliar escopo e prazo.", sent_email.body)

    def test_contact_get_renders_honeypot_field(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="website"')

    def test_missing_required_fields_is_blocked_as_spam_with_neutral_message(self):
        invalid_data = {**self.valid_data, "contact_name": ""}
        response = self.client.post(self.url, invalid_data)
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_honeypot_filled_does_not_send_email(self):
        spam_data = {**self.valid_data, "website": "https://spam.example"}
        response = self.client.post(self.url, spam_data)
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_suspicious_term_casino_does_not_send_email(self):
        spam_data = {**self.valid_data, "message": "Oferta de casino com free money imperdível"}
        response = self.client.post(self.url, spam_data)
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_many_links_does_not_send_email(self):
        spam_data = {
            **self.valid_data,
            "message": " ".join(
                [
                    "https://a.com",
                    "https://b.com",
                    "https://c.com",
                    "https://d.com",
                    "https://e.com",
                    "https://f.com",
                ]
            ),
        }
        response = self.client.post(self.url, spam_data)
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)

    def test_short_message_does_not_send_email(self):
        spam_data = {**self.valid_data, "message": "oi"}
        response = self.client.post(self.url, spam_data)
        self.assertRedirects(response, self.url, fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 0)
