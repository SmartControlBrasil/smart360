from django.test import TestCase
from django.urls import reverse

from apps.growth_engine.models import Lead, LeadInteraction
from apps.marketplace_ecom.views import PRODUCTS


class MarketplaceEcomViewTests(TestCase):
    def test_home_returns_200(self):
        response = self.client.get(reverse("marketplace_ecom:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Catálogo Técnico")

    def test_products_returns_all_products(self):
        response = self.client.get(reverse("marketplace_ecom:products"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Exibindo {len(PRODUCTS)} soluções")
        self.assertContains(response, "Littlebot")
        self.assertContains(response, "Hi Wall Inverter")
        self.assertContains(response, "Fabricante")
        self.assertContains(response, "Parceiro")

    def test_products_filter_by_brand(self):
        response = self.client.get(reverse("marketplace_ecom:products"), {"brand": "LG"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hi Wall Inverter")
        self.assertContains(response, "Fabricante: LG")
        self.assertNotContains(response, "Littlebot")

    def test_products_filter_by_supplier(self):
        response = self.client.get(reverse("marketplace_ecom:products"), {"supplier": "BHP Ar Condicionado"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "BHP Ar Condicionado")
        self.assertContains(response, "Hi Wall Inverter")
        self.assertContains(response, "Fancolete Hidronico")
        self.assertNotContains(response, "Littlebot")

    def test_products_filter_by_category(self):
        response = self.client.get(reverse("marketplace_ecom:products"), {"category": "Robótica e IA"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Littlebot")
        self.assertContains(response, "Xyron Robotics")
        self.assertNotContains(response, "Hi Wall Inverter")

    def test_products_search_by_text(self):
        response = self.client.get(reverse("marketplace_ecom:products"), {"q": "littlebot"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Littlebot")
        self.assertNotContains(response, "Orbit")

    def test_products_search_accepts_accented_query(self):
        response = self.client.get(reverse("marketplace_ecom:products"), {"q": "robô"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Littlebot")
        self.assertContains(response, "Xyron Robotics")

    def test_products_unknown_filter_shows_empty_state(self):
        response = self.client.get(reverse("marketplace_ecom:products"), {"brand": "Fabricante Inexistente"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhuma solução encontrada com esses filtros.")

    def test_products_multiple_filters_work(self):
        response = self.client.get(
            reverse("marketplace_ecom:products"),
            {"brand": "LG", "supplier": "BHP Ar Condicionado"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hi Wall Inverter")
        self.assertContains(response, "Fabricante: LG")
        self.assertContains(response, "Parceiro: BHP Ar Condicionado")
        self.assertNotContains(response, "Multi Split")

    def test_product_detail_returns_200(self):
        response = self.client.get(reverse("marketplace_ecom:product-detail", kwargs={"slug": "xyron-littlebot"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Littlebot")

    def test_unknown_product_returns_404(self):
        response = self.client.get(reverse("marketplace_ecom:product-detail", kwargs={"slug": "produto-inexistente"}))

        self.assertEqual(response.status_code, 404)

    def test_home_contains_catalog_branding(self):
        response = self.client.get("/marketplace/")

        self.assertContains(response, "Catálogo Técnico")

    def test_quote_request_valid_post_creates_lead(self):
        response = self.client.post(
            reverse("marketplace_ecom:request-quote", kwargs={"slug": "lg-hi-wall-inverter"}),
            {
                "name": "Maria Silva",
                "company": "Clima Sul",
                "email": "maria@example.com",
                "phone": "11999990000",
                "city": "Sao Paulo",
                "message": "Preciso de orçamento para climatização comercial.",
            },
        )

        self.assertRedirects(response, reverse("marketplace_ecom:product-detail", kwargs={"slug": "lg-hi-wall-inverter"}))
        lead = Lead.objects.get(email="maria@example.com")
        self.assertEqual(lead.company_name, "Clima Sul")
        self.assertEqual(lead.contact_name, "Maria Silva")
        self.assertEqual(lead.phone, "11999990000")
        self.assertEqual(lead.status, Lead.Status.NEW)
        self.assertEqual(lead.source.name, "marketplace_ecom")
        self.assertEqual(lead.metadata["product_slug"], "lg-hi-wall-inverter")
        self.assertEqual(lead.metadata["product_title"], "Hi Wall Inverter")
        self.assertEqual(lead.metadata["brand"], "LG")
        self.assertEqual(lead.metadata["supplier"], "BHP Ar Condicionado")
        self.assertEqual(lead.metadata["category"], "Ar-condicionado")
        self.assertEqual(lead.metadata["origin"], "marketplace_ecom")
        self.assertEqual(lead.metadata["request_type"], "quote_request")

    def test_quote_request_without_company_uses_contact_name_as_company_name(self):
        self.client.post(
            reverse("marketplace_ecom:request-quote", kwargs={"slug": "xyron-littlebot"}),
            {
                "name": "Joao Santos",
                "company": "",
                "email": "joao@example.com",
                "phone": "21999990000",
                "city": "Rio de Janeiro",
                "message": "Quero avaliar um robô para recepção.",
            },
        )

        lead = Lead.objects.get(email="joao@example.com")
        self.assertEqual(lead.company_name, "Joao Santos")
        self.assertEqual(lead.metadata["brand"], "Xyron Robotics")

    def test_quote_request_invalid_post_returns_errors(self):
        response = self.client.post(
            reverse("marketplace_ecom:request-quote", kwargs={"slug": "lg-hi-wall-inverter"}),
            {
                "name": "",
                "company": "Clima Sul",
                "email": "email-invalido",
                "phone": "",
                "city": "",
                "message": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Solicitar orçamento")
        self.assertTrue(response.context["quote_form"].errors)
        self.assertFalse(Lead.objects.exists())

    def test_quote_request_unknown_product_returns_404(self):
        response = self.client.post(
            reverse("marketplace_ecom:request-quote", kwargs={"slug": "produto-inexistente"}),
            {
                "name": "Maria Silva",
                "email": "maria@example.com",
                "phone": "11999990000",
                "city": "Sao Paulo",
                "message": "Preciso de orçamento.",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Lead.objects.exists())

    def test_quote_request_creates_lead_interaction(self):
        self.client.post(
            reverse("marketplace_ecom:request-quote", kwargs={"slug": "lg-hi-wall-inverter"}),
            {
                "name": "Maria Silva",
                "company": "Clima Sul",
                "email": "maria@example.com",
                "phone": "11999990000",
                "city": "Sao Paulo",
                "message": "Preciso de orçamento para climatização comercial.",
            },
        )

        lead = Lead.objects.get(email="maria@example.com")
        interaction = LeadInteraction.objects.get(lead=lead)
        self.assertEqual(interaction.interaction_type, LeadInteraction.InteractionType.NOTE)
        self.assertEqual(interaction.channel, LeadInteraction.Channel.OTHER)
        self.assertEqual(interaction.summary, "Solicitação de orçamento via marketplace.")
