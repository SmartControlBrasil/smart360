"""Fluxo público Caneca → MarketplaceOrder escopável no Admin Shell."""

from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from apps.companies.models import Company
from apps.market_core.models import MarketplaceOrder

from apps.caneca_de_garagem import dashboard_views
from apps.caneca_de_garagem.views import FACTORY_VENDOR_SLUG

User = get_user_model()


def _request_with_session(user) -> HttpRequest:
    rf = RequestFactory()
    req = rf.get("/")
    SessionMiddleware(lambda r: None).process_request(req)
    req.session.save()
    req.user = user
    return req


def _minimal_personalization_post_data(snapshot_slug: str) -> dict:
    return {
        "customer_name": "Cliente Fluxo Teste",
        "whatsapp": "11999998888",
        "email": "fluxo@teste.local",
        "quantity": "1",
        "message_or_phrase": "Mensagem de teste do fluxo.",
        "observations": "",
        "usage_type": "presente",
        "artwork_need": "nao_sei",
        "product_slug": snapshot_slug,
        "partner_slug": FACTORY_VENDOR_SLUG,
    }


class TestCanecaPublicOrderDashboardFlow(TestCase):
    databases = "__all__"

    def setUp(self):
        self.company = Company.objects.create(name="Tenant Caneca Teste", slug="tenant-caneca-teste-flow")
        self.admin = User.objects.create_superuser(
            email="admin-caneca-flow@test.local",
            password="TestPass123!",
            first_name="Admin",
        )

    def test_product_detail_post_creates_order_with_origin_and_list_detail(self):
        slug = "kit-presentes-personalizados"

        anon = Client()
        url = reverse("caneca_de_garagem:product_detail", kwargs={"slug": slug})
        response = anon.post(url, data=_minimal_personalization_post_data(slug))
        self.assertEqual(response.status_code, 302)
        code = anon.session.get("caneca_last_order_code")
        self.assertIsNotNone(code)

        order = MarketplaceOrder.objects.get(code=code)
        md = order.metadata if isinstance(order.metadata, dict) else {}
        self.assertEqual(md.get("origin"), dashboard_views.CANECA_PUBLIC_ORIGIN_STOREFRONT)
        self.assertEqual(md.get("storefront"), dashboard_views.CANECA_PUBLIC_ORIGIN_STOREFRONT)
        self.assertEqual(order.company_id, self.company.pk)
        self.assertTrue(order.items.exists())
        item = order.items.first()
        self.assertIsNotNone(item)
        self.assertTrue(hasattr(item, "customization_request"))
        self.assertIsNotNone(item.customization_request)

        req_shell = _request_with_session(self.admin)
        self.assertTrue(dashboard_views.caneca_marketplace_orders_queryset(req_shell).filter(pk=order.pk).exists())

        self.client.force_login(self.admin)
        detail_url = reverse("admin-shell:caneca-order-detail", kwargs={"order_id": order.pk})
        list_resp = self.client.get(reverse("admin-shell:caneca-order-list"))
        self.assertEqual(list_resp.status_code, 200)
        detail_resp = self.client.get(detail_url)
        self.assertEqual(detail_resp.status_code, 200)
