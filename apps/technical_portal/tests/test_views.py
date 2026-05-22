from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.technical_portal.models import ErrorCode, TechnicalArticle, TechnicalCategory


class TechnicalPortalViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="portal@smart360.local",
            password="StrongPass123",
            first_name="Portal",
        )

    def login(self):
        self.client.force_login(self.user)

    def test_can_create_categories(self):
        category = TechnicalCategory.objects.create(
            name="Ar-condicionado",
            slug="ar-condicionado",
            description="Códigos de erro e orientações iniciais.",
        )

        self.assertEqual(str(category), "Ar-condicionado")

    def test_portal_requires_authentication(self):
        response = self.client.get(reverse("technical_portal:home"))

        self.assertRedirects(
            response,
            "/login/?next=/portal/",
            fetch_redirect_response=False,
        )

    def test_portal_shows_active_categories(self):
        TechnicalCategory.objects.create(
            name="Ar-condicionado",
            slug="ar-condicionado",
            description="Códigos de erro, sintomas comuns e orientações iniciais.",
            is_active=True,
        )
        TechnicalCategory.objects.create(
            name="Categoria inativa",
            slug="categoria-inativa",
            description="Não deve aparecer.",
            is_active=False,
        )
        self.login()

        response = self.client.get(reverse("technical_portal:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ar-condicionado")
        self.assertNotContains(response, "Categoria inativa")

    def test_portal_template_contains_title(self):
        self.login()

        response = self.client.get(reverse("technical_portal:home"))

        self.assertContains(response, "Portal Técnico Smart360")

    def test_search_returns_article_for_compressor(self):
        category = TechnicalCategory.objects.create(
            name="Geladeiras",
            slug="geladeiras",
            description="Refrigeração e partida.",
        )
        TechnicalArticle.objects.create(
            category=category,
            title="Partida do compressor",
            slug="partida-do-compressor",
            summary="Diagnóstico básico de compressor.",
            content="Verifique relé, alimentação e compressor antes de trocar componentes.",
            tags="compressor, partida",
        )
        self.login()

        response = self.client.get(reverse("technical_portal:search"), {"q": "compressor"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Partida do compressor")

    def test_category_detail_returns_200(self):
        category = TechnicalCategory.objects.create(
            name="Automação",
            slug="automacao",
            description="CLPs, sensores, comandos e integração.",
        )
        self.login()

        response = self.client.get(reverse("technical_portal:category-detail", args=[category.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Automação")

    def test_seed_is_idempotent(self):
        call_command("seed_technical_portal", verbosity=0)
        first_counts = (
            TechnicalCategory.objects.count(),
            TechnicalArticle.objects.count(),
            ErrorCode.objects.count(),
        )

        call_command("seed_technical_portal", verbosity=0)
        second_counts = (
            TechnicalCategory.objects.count(),
            TechnicalArticle.objects.count(),
            ErrorCode.objects.count(),
        )

        self.assertEqual(first_counts, (6, 6, 1))
        self.assertEqual(second_counts, first_counts)
