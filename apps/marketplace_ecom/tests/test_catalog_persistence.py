from django.test import TestCase
from django.urls import reverse

from apps.growth_engine.models import Lead
from apps.marketplace_ecom.models import TechnicalProduct
from apps.marketplace_ecom.services.catalog_seed import seed_technical_catalog_from_static
from apps.marketplace_ecom.tests.base import MarketplaceCatalogTestCase


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
        display_order=5,
    )
    data.update(kwargs)
    return TechnicalProduct.objects.create(**data)


class PersistedTechnicalCatalogTests(MarketplaceCatalogTestCase):
    def test_list_includes_active_persisted_product(self):
        _persist_catalog_product()
        rsp = self.client.get(reverse("marketplace_ecom:products"))
        active_count = TechnicalProduct.objects.filter(is_active=True).count()

        self.assertEqual(rsp.status_code, 200)
        self.assertContains(rsp, "Sensor SC100 ZZ")
        self.assertContains(rsp, f"Exibindo {active_count} soluções")

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

    def test_empty_database_shows_no_public_products(self):
        TechnicalProduct.objects.all().delete()
        rsp = self.client.get(reverse("marketplace_ecom:products"))
        self.assertContains(rsp, "Exibindo 0 soluções")

    def test_quote_request_lead_metadata_for_persisted_product(self):
        _persist_catalog_product(
            slug="quote-prod-xx",
            title="Prod Cotação",
            brand="Brand X",
            supplier_name="Sup Y",
            category="Ar-condicionado",
            application_area="Laboratório",
            metadata={"product_type": "Sensor industrial"},
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


class AdminDrivenCatalogTests(MarketplaceCatalogTestCase):
    def test_new_active_product_appears_in_catalog(self):
        TechnicalProduct.objects.create(
            title="Produto Admin Novo",
            slug="produto-admin-novo",
            brand="Marca Teste",
            supplier_name="Smart Control Brasil",
            category="Linha experimental",
            short_description="Produto cadastrado via admin.",
            description="Descrição completa do produto admin.",
            application_area="Laboratório",
            is_active=True,
            display_order=1,
        )

        response = self.client.get(reverse("marketplace_ecom:products"))
        self.assertContains(response, "Produto Admin Novo")

    def test_inactive_product_disappears_from_catalog(self):
        product = TechnicalProduct.objects.get(slug="xyron-neobot")
        product.is_active = False
        product.save(update_fields=["is_active"])

        response = self.client.get(reverse("marketplace_ecom:products"))
        self.assertNotContains(response, "NeoBot")

    def test_featured_product_appears_on_home(self):
        TechnicalProduct.objects.filter(is_featured=True).update(is_featured=False)
        featured = TechnicalProduct.objects.get(slug="xyron-hostbot")
        featured.is_featured = True
        featured.save(update_fields=["is_featured"])

        response = self.client.get(reverse("marketplace_ecom:home"))
        self.assertContains(response, "HostBot")
        self.assertNotContains(response, "NeoBot")

    def test_catalog_image_fallback_renders_on_site(self):
        product = TechnicalProduct.objects.get(slug="xyron-liro-littlebot")
        product.featured_image = None
        product.metadata = {
            **(product.metadata or {}),
            "catalog_image": "institutional/eitech/img/elements/liro-robo-educacional.png",
        }
        product.save(update_fields=["featured_image", "metadata"])

        response = self.client.get(reverse("marketplace_ecom:product-detail", args=[product.slug]))
        self.assertContains(response, "institutional/eitech/img/elements/liro-robo-educacional.png")

    def test_seed_command_is_idempotent_by_slug(self):
        before = TechnicalProduct.objects.count()
        first = seed_technical_catalog_from_static()
        second = seed_technical_catalog_from_static()

        self.assertEqual(TechnicalProduct.objects.count(), before)
        self.assertGreater(first["total"], 0)
        self.assertEqual(second["created"], 0)
        self.assertGreater(second["updated"], 0)
