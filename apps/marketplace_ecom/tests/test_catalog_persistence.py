from django.test import TestCase
from django.urls import reverse

from apps.growth_engine.models import Lead
from apps.marketplace_ecom.models import TechnicalProduct
from apps.marketplace_ecom.views import PRODUCTS


def _persist_catalog_product(**kwargs):
    data = dict(
        title="Sensor SC100 ZZ",
        slug="sensor-sc100-zz-catalog-test",
        brand="Fabricante Persist",
        supplier_name="Fornecedor Persist",
        category="Robótica e IA",
        short_description="Resumo técnico do sensor.",
        description="Descrição longa persistida.",
        application_area="Indústria 4.0",
        is_active=True,
        is_featured=False,
    )
    data.update(kwargs)
    return TechnicalProduct.objects.create(**data)


class PersistedTechnicalCatalogTests(TestCase):
    def test_list_includes_active_persisted_product(self):
        _persist_catalog_product()
        rsp = self.client.get(reverse("marketplace_ecom:products"))
        self.assertEqual(rsp.status_code, 200)
        self.assertContains(rsp, "Sensor SC100 ZZ")
        self.assertContains(rsp, f"Exibindo {len(PRODUCTS) + 1} soluções")

    def test_inactive_product_not_in_list(self):
        _persist_catalog_product(slug="hidden-prod-xx", title="Oculto catálogo", is_active=False)
        rsp = self.client.get(reverse("marketplace_ecom:products"))
        self.assertNotContains(rsp, "Oculto catálogo")

    def test_detail_shows_active_persisted_product(self):
        _persist_catalog_product()
        rsp = self.client.get(
            reverse(
                "marketplace_ecom:product-detail",
                kwargs={"slug": "sensor-sc100-zz-catalog-test"},
            ),
        )
        self.assertEqual(rsp.status_code, 200)
        self.assertContains(rsp, "Descrição longa persistida.")

    def test_detail_inactive_product_returns_404(self):
        _persist_catalog_product(slug="inactive-prod-xx", title="Inactive", is_active=False)
        rsp = self.client.get(
            reverse("marketplace_ecom:product-detail", kwargs={"slug": "inactive-prod-xx"}),
        )
        self.assertEqual(rsp.status_code, 404)

    def test_catalog_fallback_when_table_empty(self):
        self.assertFalse(TechnicalProduct.objects.exists())
        rsp = self.client.get(reverse("marketplace_ecom:products"))
        self.assertContains(rsp, f"Exibindo {len(PRODUCTS)} soluções")
        self.assertContains(rsp, "LIRO / LittleBot")

    def test_quote_request_lead_metadata_for_persisted_product(self):
        _persist_catalog_product(
            slug="quote-prod-xx",
            title="Prod Cotação",
            brand="Brand X",
            supplier_name="Sup Y",
            category="Ar-condicionado",
            application_area="Laboratório",
        )
        self.client.post(
            reverse("marketplace_ecom:request-quote", kwargs={"slug": "quote-prod-xx"}),
            {
                "name": "User Test",
                "company": "Emp Test",
                "email": "userquote@example.com",
                "phone": "11998887777",
                "city": "SP",
                "message": "Quero cotação",
            },
        )
        lead = Lead.objects.get(email="userquote@example.com")
        self.assertEqual(lead.metadata["product_slug"], "quote-prod-xx")
        self.assertEqual(lead.metadata["product_title"], "Prod Cotação")
        self.assertEqual(lead.metadata["brand"], "Brand X")
        self.assertEqual(lead.metadata["supplier"], "Sup Y")
        self.assertEqual(lead.metadata["category"], "Ar-condicionado")
        self.assertEqual(lead.metadata["application_area"], "Laboratório")
        self.assertEqual(lead.metadata["origin"], "marketplace_ecom")
