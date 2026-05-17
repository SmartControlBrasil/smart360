from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User

from apps.market_core.models import MarketplaceOrder, MarketplaceOrderItem, MarketplaceProduct, MarketplaceVendor
from ..models import CreativeStoreProfile, CustomizationTemplate, ProductionJob


class CanecaDeGaragemApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="caneca@smart360.local",
            password="StrongPass123",
            first_name="Caneca",
        )
        self.customer = User.objects.create_user(
            email="cliente@smart360.local",
            password="StrongPass123",
            first_name="Cliente",
        )
        self.vendor = MarketplaceVendor.objects.create(name="Loja Criativa", slug="loja-criativa", owner=self.user)
        self.product = MarketplaceProduct.objects.create(
            vendor=self.vendor,
            name="Caneca Personalizada",
            slug="caneca-personalizada",
            sku="CDG-001",
            base_price="39.90",
        )
        self.order = MarketplaceOrder.objects.create(code="PED-0001", customer=self.customer, total_amount="39.90")
        self.order_item = MarketplaceOrderItem.objects.create(order=self.order, product=self.product, quantity=1, unit_price="39.90")
        self.client.force_authenticate(self.user)

    def test_create_store_profile(self):
        response = self.client.post(
            reverse("cdg-store-profiles-list"),
            {
                "vendor": self.vendor.id,
                "display_name": "Loja Criativa Oficial",
                "profile_type": "mixed",
                "production_capabilities": ["sublimacao", "camisetas"],
                "is_internal_factory": False,
                "lead_time_days": 4,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CreativeStoreProfile.objects.filter(vendor=self.vendor).exists())

    def test_create_customization_request(self):
        template = CustomizationTemplate.objects.create(
            product=self.product,
            template_name="Template Base Caneca",
            allowed_text_fields=["nome", "frase"],
            allowed_image_upload=True,
            max_images=2,
        )
        response = self.client.post(
            reverse("cdg-customization-requests-list"),
            {
                "order_item": self.order_item.id,
                "customization_template": template.id,
                "customer_text": {"nome": "Ana", "frase": "Bom dia"},
                "uploaded_assets": ["logo.png"],
                "font_choice": "Montserrat",
                "color_choice": "Preto",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["font_choice"], "Montserrat")

    def test_create_production_job_bootstraps_steps(self):
        profile = CreativeStoreProfile.objects.create(
            vendor=self.vendor,
            display_name="Fabrica Interna",
            profile_type="mixed",
            production_capabilities=["sublimacao"],
            is_internal_factory=True,
            lead_time_days=2,
        )
        response = self.client.post(
            reverse("cdg-production-jobs-list"),
            {
                "order": self.order.id,
                "order_item": self.order_item.id,
                "vendor": self.vendor.id,
                "internal_factory": profile.id,
                "job_type": "sublimation",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        job = ProductionJob.objects.get(order_item=self.order_item)
        self.assertEqual(job.steps.count(), 4)
        self.assertEqual(job.queue_position, 1)
