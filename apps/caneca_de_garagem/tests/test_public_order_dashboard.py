"""Fluxo público Caneca → MarketplaceOrder escopável no Admin Shell."""

from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from apps.companies.models import Company
from apps.market_core.models import MarketplaceOrder

from apps.caneca_de_garagem import dashboard_views
from apps.caneca_de_garagem.models import ProductionJob
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

    def test_create_production_job_idempotent_queue_and_detail(self):
        slug = "kit-presentes-personalizados"
        anon = Client()
        anon.post(
            reverse("caneca_de_garagem:product_detail", kwargs={"slug": slug}),
            data=_minimal_personalization_post_data(slug),
        )
        order = MarketplaceOrder.objects.latest("id")
        gen_url = reverse(
            dashboard_views.CANECA_ADMIN_URL_ORDER_CREATE_PRODUCTION,
            kwargs={"order_id": order.pk},
        )

        self.client.force_login(self.admin)
        r1 = self.client.post(gen_url, follow=False)
        self.assertEqual(r1.status_code, 302)
        self.assertEqual(ProductionJob.objects.filter(order_id=order.pk).count(), 1)
        job = ProductionJob.objects.get(order_id=order.pk)
        self.assertEqual(job.job_type, ProductionJob.JobType.ART_PREP)
        self.assertEqual(job.status, ProductionJob.Status.QUEUED)
        order.refresh_from_db()
        self.assertEqual(order.status, MarketplaceOrder.Status.IN_PRODUCTION)

        r2 = self.client.post(gen_url, follow=False)
        self.assertEqual(r2.status_code, 302)
        self.assertEqual(ProductionJob.objects.filter(order_id=order.pk).count(), 1)

        req = _request_with_session(self.admin)
        self.assertTrue(dashboard_views.caneca_production_orders_queryset(req).filter(pk=order.pk).exists())

        detail = self.client.get(reverse("admin-shell:caneca-order-detail", kwargs={"order_id": order.pk}))
        self.assertEqual(detail.status_code, 200)
        body = detail.content.decode().lower()
        self.assertIn("art preparation", body)
        self.assertIn(str(job.id).lower(), body)
        self.assertNotIn("gerar produção".lower(), body)

    def test_production_job_start_complete_and_queue_visibility(self):
        slug = "kit-presentes-personalizados"
        anon = Client()
        anon.post(
            reverse("caneca_de_garagem:product_detail", kwargs={"slug": slug}),
            data=_minimal_personalization_post_data(slug),
        )
        order = MarketplaceOrder.objects.latest("id")

        self.client.force_login(self.admin)
        self.client.post(
            reverse(dashboard_views.CANECA_ADMIN_URL_ORDER_CREATE_PRODUCTION, kwargs={"order_id": order.pk}),
            follow=False,
        )
        job = ProductionJob.objects.get(order_id=order.pk)

        order.status = MarketplaceOrder.Status.PAID
        order.save(update_fields=["status", "updated_at"])

        start_resp = self.client.post(
            reverse("admin-shell:caneca-production-job-start", kwargs={"job_id": job.pk}),
            follow=False,
        )
        self.assertEqual(start_resp.status_code, 302)
        job.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(job.status, ProductionJob.Status.IN_PROGRESS)
        self.assertIsNotNone(job.started_at)
        self.assertEqual(order.status, MarketplaceOrder.Status.IN_PRODUCTION)

        complete_resp = self.client.post(
            reverse("admin-shell:caneca-production-job-complete", kwargs={"job_id": job.pk}),
            follow=False,
        )
        self.assertEqual(complete_resp.status_code, 302)
        job.refresh_from_db()
        self.assertEqual(job.status, ProductionJob.Status.COMPLETED)
        self.assertIsNotNone(job.completed_at)
        self.assertEqual(ProductionJob.objects.filter(order_id=order.pk).count(), 1)

        queue_resp = self.client.get(reverse("admin-shell:caneca-production-list"))
        self.assertEqual(queue_resp.status_code, 200)
        body = queue_resp.content.decode().lower()
        self.assertIn(order.code.lower(), body)
        self.assertIn("preparação de arte", body)
        self.assertIn("concluído", body)

    def test_production_job_status_actions_require_caneca_scope(self):
        outside_order = MarketplaceOrder.objects.create(
            code="OUT-SCOPE-1",
            company=self.company,
            status=MarketplaceOrder.Status.PAID,
            metadata={"origin": "outside"},
        )
        outside_job = ProductionJob.objects.create(
            order=outside_order,
            job_type=ProductionJob.JobType.ART_PREP,
            status=ProductionJob.Status.QUEUED,
        )

        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("admin-shell:caneca-production-job-start", kwargs={"job_id": outside_job.pk}),
            follow=False,
        )
        self.assertEqual(resp.status_code, 404)
        outside_job.refresh_from_db()
        self.assertEqual(outside_job.status, ProductionJob.Status.QUEUED)
        self.assertIsNone(outside_job.started_at)

    def test_caneca_order_complete_does_not_finalize_without_production_job(self):
        slug = "kit-presentes-personalizados"
        anon = Client()
        anon.post(
            reverse("caneca_de_garagem:product_detail", kwargs={"slug": slug}),
            data=_minimal_personalization_post_data(slug),
        )
        order = MarketplaceOrder.objects.latest("id")

        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("admin-shell:caneca-order-complete", kwargs={"order_id": order.pk}),
            follow=False,
        )
        self.assertEqual(resp.status_code, 302)
        order.refresh_from_db()
        self.assertNotEqual(order.status, MarketplaceOrder.Status.DELIVERED)

    def test_caneca_order_complete_does_not_finalize_with_queued_job(self):
        slug = "kit-presentes-personalizados"
        anon = Client()
        anon.post(
            reverse("caneca_de_garagem:product_detail", kwargs={"slug": slug}),
            data=_minimal_personalization_post_data(slug),
        )
        order = MarketplaceOrder.objects.latest("id")

        self.client.force_login(self.admin)
        self.client.post(
            reverse(dashboard_views.CANECA_ADMIN_URL_ORDER_CREATE_PRODUCTION, kwargs={"order_id": order.pk}),
            follow=False,
        )

        resp = self.client.post(
            reverse("admin-shell:caneca-order-complete", kwargs={"order_id": order.pk}),
            follow=False,
        )
        self.assertEqual(resp.status_code, 302)
        order.refresh_from_db()
        self.assertNotEqual(order.status, MarketplaceOrder.Status.DELIVERED)

        detail = self.client.get(reverse("admin-shell:caneca-order-detail", kwargs={"order_id": order.pk}))
        self.assertEqual(detail.status_code, 200)
        self.assertIn("Finalize todos os jobs de produção antes de concluir o pedido.", detail.content.decode())

    def test_caneca_order_complete_does_not_finalize_with_in_progress_job(self):
        slug = "kit-presentes-personalizados"
        anon = Client()
        anon.post(
            reverse("caneca_de_garagem:product_detail", kwargs={"slug": slug}),
            data=_minimal_personalization_post_data(slug),
        )
        order = MarketplaceOrder.objects.latest("id")

        self.client.force_login(self.admin)
        self.client.post(
            reverse(dashboard_views.CANECA_ADMIN_URL_ORDER_CREATE_PRODUCTION, kwargs={"order_id": order.pk}),
            follow=False,
        )
        job = ProductionJob.objects.get(order_id=order.pk)
        job.status = ProductionJob.Status.IN_PROGRESS
        job.save(update_fields=["status", "updated_at"])

        resp = self.client.post(
            reverse("admin-shell:caneca-order-complete", kwargs={"order_id": order.pk}),
            follow=False,
        )
        self.assertEqual(resp.status_code, 302)
        order.refresh_from_db()
        self.assertNotEqual(order.status, MarketplaceOrder.Status.DELIVERED)

    def test_caneca_order_complete_finalizes_when_all_jobs_completed(self):
        slug = "kit-presentes-personalizados"
        anon = Client()
        anon.post(
            reverse("caneca_de_garagem:product_detail", kwargs={"slug": slug}),
            data=_minimal_personalization_post_data(slug),
        )
        order = MarketplaceOrder.objects.latest("id")

        self.client.force_login(self.admin)
        self.client.post(
            reverse(dashboard_views.CANECA_ADMIN_URL_ORDER_CREATE_PRODUCTION, kwargs={"order_id": order.pk}),
            follow=False,
        )
        job = ProductionJob.objects.get(order_id=order.pk)
        job.status = ProductionJob.Status.COMPLETED
        job.save(update_fields=["status", "updated_at"])

        detail = self.client.get(reverse("admin-shell:caneca-order-detail", kwargs={"order_id": order.pk}))
        self.assertEqual(detail.status_code, 200)
        self.assertIn("Finalizar pedido", detail.content.decode())

        resp = self.client.post(
            reverse("admin-shell:caneca-order-complete", kwargs={"order_id": order.pk}),
            follow=False,
        )
        self.assertEqual(resp.status_code, 302)
        order.refresh_from_db()
        status_codes = {code for code, _ in MarketplaceOrder.Status.choices}
        completed_status = getattr(MarketplaceOrder.Status, "COMPLETED", "completed")
        expected_status = MarketplaceOrder.Status.DELIVERED if MarketplaceOrder.Status.DELIVERED in status_codes else completed_status
        self.assertEqual(order.status, expected_status)

    def test_caneca_order_complete_requires_caneca_scope(self):
        outside_order = MarketplaceOrder.objects.create(
            code="OUT-SCOPE-COMPLETE",
            company=self.company,
            status=MarketplaceOrder.Status.IN_PRODUCTION,
            metadata={"origin": "outside"},
        )
        ProductionJob.objects.create(
            order=outside_order,
            job_type=ProductionJob.JobType.ART_PREP,
            status=ProductionJob.Status.COMPLETED,
        )

        self.client.force_login(self.admin)
        resp = self.client.post(
            reverse("admin-shell:caneca-order-complete", kwargs={"order_id": outside_order.pk}),
            follow=False,
        )
        self.assertEqual(resp.status_code, 404)
        outside_order.refresh_from_db()
        self.assertEqual(outside_order.status, MarketplaceOrder.Status.IN_PRODUCTION)

