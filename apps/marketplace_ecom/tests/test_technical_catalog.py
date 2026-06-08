from django.test import TestCase
from django.urls import reverse

from apps.growth_engine.models import Lead
from apps.marketplace_ecom.catalog import DEFAULT_IMAGE
from apps.marketplace_ecom.views import get_products


QUOTE_DATA = {
    "name": "Contato Técnico",
    "company": "Indústria Teste",
    "email": "contato@example.com",
    "phone": "11999990000",
    "city": "São Paulo",
    "message": "Quero avaliar esta solução.",
}


class MarketplaceTechnicalCatalogTests(TestCase):
    def test_list_contains_xyron_and_mitsubishi_products(self):
        response = self.client.get(reverse("marketplace_ecom:products"))

        self.assertContains(response, "NeoBot")
        self.assertContains(response, "CLPs Mitsubishi MELSEC")
        self.assertContains(response, "Xyron Robotics")
        self.assertContains(response, "Mitsubishi Electric")

    def test_neobot_detail_shows_specs_autonomy_and_charging(self):
        response = self.client.get(reverse("marketplace_ecom:product-detail", args=["xyron-neobot"]))

        self.assertContains(response, "Ficha técnica")
        self.assertContains(response, "Autonomia")
        self.assertContains(response, "até 10 horas")
        self.assertContains(response, "Carregamento")
        self.assertContains(response, "aproximadamente 9 horas")

    def test_hygibot_detail_shows_cleaning_and_not_buddy(self):
        response = self.client.get(reverse("marketplace_ecom:product-detail", args=["xyron-hygibot-dune-bot"]))

        self.assertContains(response, "Limpeza autônoma")
        self.assertContains(response, "Autonomia")
        self.assertContains(response, "4 horas")
        self.assertNotContains(response, "Buddy Bot")

    def test_mitsubishi_melsec_detail_loads(self):
        response = self.client.get(reverse("marketplace_ecom:product-detail", args=["mitsubishi-clp-melsec"]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CLPs Mitsubishi MELSEC")
        self.assertContains(response, "Controladores lógicos programáveis")
        self.assertContains(response, "FX5U")

    def test_search_for_cleaning_robot_finds_hygibot(self):
        response = self.client.get(reverse("marketplace_ecom:products"), {"q": "robô de limpeza"})

        self.assertContains(response, "HygiBot / Dune Bot")
        self.assertNotContains(response, "Buddy Bot")

    def test_search_for_mitsubishi_clp_finds_melsec(self):
        response = self.client.get(reverse("marketplace_ecom:products"), {"q": "Mitsubishi CLP"})

        self.assertContains(response, "CLPs Mitsubishi MELSEC")
        self.assertNotContains(response, "NeoBot")

    def test_xyron_quote_creates_complete_lead_metadata(self):
        self.client.post(reverse("marketplace_ecom:request-quote", args=["xyron-neobot"]), QUOTE_DATA)

        metadata = Lead.objects.get(email=QUOTE_DATA["email"]).metadata
        self.assertEqual(metadata["product_title"], "NeoBot")
        self.assertEqual(metadata["product_slug"], "xyron-neobot")
        self.assertEqual(metadata["brand"], "Xyron Robotics")
        self.assertEqual(metadata["category"], "Robótica de atendimento")
        self.assertEqual(metadata["product_type"], "Robô recepcionista inteligente")
        self.assertEqual(metadata["origin"], "marketplace_ecom")

    def test_mitsubishi_quote_creates_complete_lead_metadata(self):
        self.client.post(reverse("marketplace_ecom:request-quote", args=["mitsubishi-clp-melsec"]), QUOTE_DATA)

        metadata = Lead.objects.get(email=QUOTE_DATA["email"]).metadata
        self.assertEqual(metadata["product_title"], "CLPs Mitsubishi MELSEC")
        self.assertEqual(metadata["brand"], "Mitsubishi Electric")
        self.assertEqual(metadata["category"], "Automação industrial")
        self.assertEqual(metadata["product_type"], "Controladores lógicos programáveis")
        self.assertEqual(metadata["origin"], "marketplace_ecom")

    def test_all_catalog_products_use_neutral_default_image(self):
        products = get_products()

        self.assertTrue(products)
        self.assertTrue(all(product["image"] == DEFAULT_IMAGE for product in products))
        response = self.client.get(reverse("marketplace_ecom:products"))
        self.assertContains(response, "marketplace/ecom/img/template/devices.svg")

    def test_public_pages_do_not_offer_retail_flows(self):
        for route in ("marketplace_ecom:home", "marketplace_ecom:products"):
            response = self.client.get(reverse(route))
            content = response.content.decode().casefold()
            self.assertNotIn("checkout", content)
            self.assertNotIn("pagamento", content)
            self.assertNotIn("carrinho", content)
