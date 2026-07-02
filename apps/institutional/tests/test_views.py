from django.conf import settings
from django.core import mail
from django.test import SimpleTestCase, override_settings
from django.urls import reverse

from apps.institutional.xyron_robots import XYRON_ROBOTS

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
            "institutional:engenharia_embarcada",
            "institutional:representada_mitsubishi_automacao",
            "institutional:service_manutencao_tpm_confiabilidade",
            "institutional:service_automacao_industrial_clps",
            "institutional:service_robotica_integracao",
            "institutional:parceiro_xyron_robotics",
            "institutional:xyron_robotics",
            "institutional:xyron_liro_littlebot",
            "institutional:seguranca_da_informacao",
            "institutional:sites_sistemas_marketing",
        ]

        for route_name in route_names:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)

    def test_home_uses_index_template_and_institutional_content(self):
        response = self.client.get(reverse("institutional:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "institutional/eitech/pages/index.html")
        self.assertContains(response, "Smart Control Brasil")
        self.assertNotContains(response, "em construção", status_code=200)
        self.assertNotContains(response, "coming soon", status_code=200)

    def test_xyron_robotics_page_uses_partner_template(self):
        response = self.client.get(reverse("institutional:parceiro_xyron_robotics"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "institutional/eitech/pages/xyron-robotics.html"
        )
        self.assertContains(response, "institutional/eitech/css/scb-xyron.css")
        self.assertContains(response, "Xyron Robotics no Brasil | Robôs para Educação, Segurança, Limpeza e Atendimento")
        self.assertContains(response, "Conheça a linha Xyron Robotics com a Smart Control Brasil: robôs para educação, recepção, segurança, limpeza, atendimento, cuidado assistido e áreas externas.")
        self.assertContains(response, "CollectionPage")
        self.assertContains(response, 'class="xyron-page xyron-overview-page"')
        self.assertContains(response, 'xyron-dark-section')
        self.assertContains(response, 'xyron-robot-showcase')
        self.assertContains(response, 'xyron-robot-row')
        self.assertContains(response, "Linha Xyron Robotics")
        self.assertContains(response, "<h1", count=1)
        self.assertContains(response, "Saber mais")
        self.assertContains(response, "Como a Smart Control Brasil conduz projetos com robôs Xyron")
        self.assertNotContains(response, "Ficha técnica e recursos")
        self.assertNotContains(response, "Capacidade da bateria")
        self.assertNotContains(response, "Solução personalizada")

    def test_xyron_robotics_solutions_url_renders_vitrine(self):
        response = self.client.get(reverse("institutional:xyron_robotics"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "institutional/eitech/pages/xyron-robotics.html")
        self.assertContains(response, "Linha Xyron Robotics")

    def test_xyron_robotics_page_links_to_all_robot_details(self):
        response = self.client.get(reverse("institutional:parceiro_xyron_robotics"))

        self.assertEqual(response.status_code, 200)
        for robot in XYRON_ROBOTS:
            with self.subTest(robot=robot["slug"]):
                self.assertContains(
                    response,
                    reverse("institutional:xyron_robot_detail", args=[robot["slug"]]),
                )
        self.assertContains(response, "MowerBot")

    def test_all_xyron_robot_detail_pages_render(self):
        for robot in XYRON_ROBOTS:
            with self.subTest(robot=robot["slug"]):
                response = self.client.get(
                    reverse("institutional:xyron_robot_detail", args=[robot["slug"]])
                )

                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(
                    response, "institutional/eitech/pages/xyron-liro-littlebot.html"
                )
                self.assertContains(response, robot["name"])
                self.assertContains(response, robot["seo_title"])
                self.assertContains(response, robot["meta_description"])
                self.assertContains(response, f"<h1>{robot['name']}</h1>", html=True)
                self.assertContains(response, "<h1", count=1)
                self.assertContains(response, "Product")
                self.assertContains(response, "Xyron Robotics")
                self.assertContains(response, "Robôs Xyron")
                self.assertContains(response, "Ver mais robôs Xyron")
                self.assertContains(response, "Funções principais")
                self.assertContains(response, "Ficha técnica e recursos")
                self.assertContains(response, "Aplicações e benefícios")
                self.assertContains(response, "Cuidados comerciais")
                self.assertContains(response, "Perguntas frequentes")
                self.assertContains(response, "institutional/eitech/css/scb-xyron.css")
                self.assertContains(response, reverse("institutional:contact"))
                self.assertContains(response, reverse("institutional:xyron_robotics"))
                self.assertNotContains(response, "hero3-section-area")

    def test_xyron_robot_sidebar_excludes_current_robot(self):
        expected_count = len(XYRON_ROBOTS) - 1

        for robot in XYRON_ROBOTS:
            with self.subTest(robot=robot["slug"]):
                response = self.client.get(
                    reverse("institutional:xyron_robot_detail", args=[robot["slug"]])
                )

                sidebar_robots = response.context["sidebar_robots"]
                sidebar_slugs = [item["slug"] for item in sidebar_robots]
                self.assertEqual(len(sidebar_robots), expected_count)
                self.assertNotIn(robot["slug"], sidebar_slugs)
                self.assertContains(response, 'data-robot-slug="', count=expected_count)

    def test_xyron_robot_detail_sidebar_does_not_link_to_current_page(self):
        for robot in XYRON_ROBOTS:
            with self.subTest(robot=robot["slug"]):
                response = self.client.get(
                    reverse("institutional:xyron_robot_detail", args=[robot["slug"]])
                )

                current_url = reverse("institutional:xyron_robot_detail", args=[robot["slug"]])
                sidebar_slugs = [item["slug"] for item in response.context["sidebar_robots"]]
                related_slugs = [item["slug"] for item in response.context["related_robots"]]
                self.assertNotIn(robot["slug"], sidebar_slugs)
                self.assertNotIn(robot["slug"], related_slugs)
                self.assertNotContains(response, f'href="{current_url}"')

    def test_sitemap_includes_xyron_overview_and_robot_pages(self):
        response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("institutional:xyron_robotics"))
        for robot in XYRON_ROBOTS:
            with self.subTest(robot=robot["slug"]):
                self.assertContains(
                    response,
                    reverse("institutional:xyron_robot_detail", args=[robot["slug"]]),
                )

    def test_xyron_robot_detail_keeps_consultative_guardrails(self):
        checks = [
            ("liro-littlebot", "não substitui o professor"),
            ("patrol-orbit", "não é substituir completamente equipes de segurança"),
            ("waiterbot", "não deve ser tratado como substituto completo de garçons"),
            ("carebot", "não realiza promessa médica"),
            ("mowerbot", "corte de grama"),
        ]

        for slug, text in checks:
            with self.subTest(slug=slug):
                response = self.client.get(reverse("institutional:xyron_robot_detail", args=[slug]))

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, text)

    def test_xyron_robot_detail_referenced_images_exist(self):
        from pathlib import Path

        static_root = Path(settings.BASE_DIR) / "static"
        missing = []
        for robot in XYRON_ROBOTS:
            image_paths = [robot["image"], *robot.get("secondary_images", [])]
            for image_path in image_paths:
                if not (static_root / image_path).exists():
                    missing.append((robot["slug"], image_path))

        self.assertEqual(missing, [])

    def test_xyron_robot_detail_contains_other_robot_links(self):
        response = self.client.get(
            reverse("institutional:xyron_robot_detail", args=["mowerbot"])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("institutional:xyron_robot_detail", args=["liro-littlebot"]),
        )
        self.assertContains(
            response,
            reverse("institutional:xyron_robot_detail", args=["carebot"]),
        )
        self.assertEqual(response.context["robot"]["slug"], "mowerbot")

    def test_xyron_liro_legacy_url_name_still_renders_detail(self):
        response = self.client.get(reverse("institutional:xyron_liro_littlebot"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LIRO / LittleBot")
        self.assertContains(response, "O LIRO substitui o professor?")
        self.assertEqual(response.context["robot"]["slug"], "liro-littlebot")

    def test_unknown_xyron_robot_returns_404(self):
        response = self.client.get("/solucoes/xyron-robotics/nao-existe/")

        self.assertEqual(response.status_code, 404)

    def test_engenharia_embarcada_canonical_url(self):
        self.assertEqual(
            reverse("institutional:engenharia_embarcada"),
            "/engenharia-embarcada/",
        )

    def test_engenharia_embarcada_page_uses_new_template(self):
        response = self.client.get(reverse("institutional:engenharia_embarcada"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "institutional/eitech/pages/engenharia_embarcada.html"
        )
        self.assertContains(response, "Engenharia Embarcada")

    def test_legacy_refrigeracao_url_redirects_to_engenharia_embarcada(self):
        response = self.client.get("/parceiros/refrigeracao/", follow=False)

        self.assertRedirects(
            response,
            reverse("institutional:engenharia_embarcada"),
            status_code=301,
            fetch_redirect_response=False,
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

    def test_home_uses_shared_action_layout_classes(self):
        response = self.client.get(reverse("institutional:home"))

        self.assertContains(response, "scb-home-hero-actions")
        self.assertContains(response, "scb-home-final-actions")

    def test_web_systems_page_has_expected_visual_contract(self):
        response = self.client.get(
            reverse("institutional:service_sistemas_web_aplicativos")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "institutional/eitech/pages/service-sistemas-web-aplicativos.html",
        )
        self.assertContains(response, "service-web-systems-page")
        self.assertContains(response, "institutional/eitech/css/scb-service.css")
        self.assertContains(response, "Solicitar diagnóstico")
        self.assertContains(response, "Falar com a Lívia")

    def test_maintenance_uses_shared_service_styles_only(self):
        response = self.client.get(
            reverse("institutional:service_manutencao_tpm_confiabilidade")
        )

        self.assertContains(response, "institutional/eitech/css/scb-service.css")
        self.assertNotContains(response, "scb-maintenance.css")
        self.assertContains(response, "scb-maintenance-scope-note")



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
