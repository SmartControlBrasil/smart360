from django.conf import settings
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
