from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import resolve, reverse
from django.utils import timezone

from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.companies.models import Company, Membership, SiteMembership
from apps.smart_system.models import Asset, AssetCategory, MaintenanceClient, OperationalSite, ServiceOrder, WorkLog
from apps.technical_portal.models import ErrorCode, TechnicalArticle, TechnicalCategory
from apps.technical_portal.views import (
    ClientAssetListView,
    ClientPortalDashboardView,
    ClientServiceOrderCreateView,
    ClientServiceOrderDetailView,
    ClientServiceOrderListView,
    TechnicalCategoryDetailView,
    TechnicalPortalSearchView,
)


class TechnicalPortalViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        bootstrap_smart_system_access()

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="portal@smart360.local",
            password="StrongPass123",
            first_name="Portal",
            user_type="client",
        )

    def login(self):
        self.client.force_login(self.user)

    def create_scope(self):
        company = Company.objects.create(name="Cliente Portal", slug="cliente-portal")
        maintenance_client = MaintenanceClient.objects.create(company=company, display_name="Cliente Portal")
        site = OperationalSite.objects.create(maintenance_client=maintenance_client, name="Unidade A")
        category = AssetCategory.objects.create(name="Equipamentos Portal", slug="equipamentos-portal")
        asset = Asset.objects.create(
            operational_site=site,
            category=category,
            asset_tag="EQ-001",
            name="Compressor 01",
        )
        Membership.objects.create(user=self.user, company=company, status=Membership.Status.ACTIVE, is_primary=True)
        SiteMembership.objects.create(user=self.user, company=company, site=site, status=SiteMembership.Status.ACTIVE, is_primary=True)
        return company, maintenance_client, site, asset

    def create_order(self, maintenance_client, site, asset=None, *, order_number="SS-TESTE-0001"):
        return ServiceOrder.objects.create(
            order_number=order_number,
            client=maintenance_client,
            operational_site=site,
            asset=asset,
            maintenance_type=ServiceOrder.MaintenanceType.CORRECTIVE,
            priority=ServiceOrder.Priority.MEDIUM,
            status=ServiceOrder.Status.OPEN,
            source=ServiceOrder.Source.MANUAL,
            title="Chamado em aberto",
            description="Equipamento com falha intermitente.",
        )

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

    def test_portal_url_map_is_external_client_portal(self):
        expected = {
            "/portal/": ClientPortalDashboardView,
            "/portal/chamados/": ClientServiceOrderListView,
            "/portal/chamados/novo/": ClientServiceOrderCreateView,
            "/portal/chamados/1/": ClientServiceOrderDetailView,
            "/portal/equipamentos/": ClientAssetListView,
            "/portal/search/": TechnicalPortalSearchView,
            "/portal/category/teste/": TechnicalCategoryDetailView,
        }

        for url, view_class in expected.items():
            self.assertIs(resolve(url).func.view_class, view_class)

    def test_portal_dashboard_uses_client_portal_template(self):
        self.create_scope()
        self.login()

        response = self.client.get(reverse("technical_portal:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "client_portal/dashboard.html")
        self.assertContains(response, "Portal do Cliente")

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
        self.create_scope()
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
        self.create_scope()
        self.login()

        response = self.client.get(reverse("technical_portal:category-detail", args=[category.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Automação")

    def test_authorized_client_creates_real_service_order(self):
        company, maintenance_client, site, asset = self.create_scope()
        assign_smart_system_role(self.user, "requester", company=company)
        self.login()

        response = self.client.post(
            reverse("technical_portal:service-order-create"),
            {
                "operational_site": site.pk,
                "asset": asset.pk,
                "priority": ServiceOrder.Priority.HIGH,
                "description": "Equipamento parado no turno da manhã.",
            },
        )

        self.assertEqual(response.status_code, 302)
        order = ServiceOrder.objects.get()
        self.assertEqual(order.client, maintenance_client)
        self.assertEqual(order.operational_site, site)
        self.assertEqual(order.asset, asset)
        self.assertEqual(order.status, ServiceOrder.Status.OPEN)
        self.assertEqual(order.maintenance_type, ServiceOrder.MaintenanceType.CORRECTIVE)
        self.assertTrue(order.order_number.startswith("SS-"))

    def test_readonly_client_does_not_create_service_order(self):
        company, _, site, asset = self.create_scope()
        assign_smart_system_role(self.user, "client-readonly", company=company)
        self.login()

        response = self.client.post(
            reverse("technical_portal:service-order-create"),
            {
                "operational_site": site.pk,
                "asset": asset.pk,
                "priority": ServiceOrder.Priority.HIGH,
                "description": "Equipamento parado.",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ServiceOrder.objects.exists())

    def test_common_user_cannot_access_out_of_scope_order(self):
        self.create_scope()
        other_company = Company.objects.create(name="Outro Cliente", slug="outro-cliente")
        other_client = MaintenanceClient.objects.create(company=other_company, display_name="Outro Cliente")
        other_site = OperationalSite.objects.create(maintenance_client=other_client, name="Unidade Externa")
        order = self.create_order(other_client, other_site, order_number="SS-FORA-0001")
        self.login()

        response = self.client.get(reverse("technical_portal:service-order-detail", args=[order.pk]))

        self.assertEqual(response.status_code, 404)

    def test_detail_does_not_expose_internal_worklog_notes(self):
        _, maintenance_client, site, asset = self.create_scope()
        order = self.create_order(maintenance_client, site, asset=asset)
        WorkLog.objects.create(
            service_order=order,
            user=self.user,
            started_at=timezone.now(),
            labor_minutes=30,
            notes="Nota interna: trocar fornecedor e revisar custo.",
        )
        self.login()

        response = self.client.get(reverse("technical_portal:service-order-detail", args=[order.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Atendimento tecnico registrado")
        self.assertNotContains(response, "Nota interna")
        self.assertNotContains(response, "trocar fornecedor")

    def test_client_membership_alone_does_not_access_admin_dashboard(self):
        self.create_scope()
        self.login()

        response = self.client.get(reverse("admin-shell:dashboard-entry"))

        self.assertEqual(response.status_code, 403)

    def test_main_routes_return_200(self):
        _, maintenance_client, site, asset = self.create_scope()
        order = self.create_order(maintenance_client, site, asset=asset, order_number="SS-ROTA-0001")
        assign_smart_system_role(self.user, "requester", company=maintenance_client.company)
        category = TechnicalCategory.objects.create(
            name="Automação",
            slug="automacao",
            description="CLPs, sensores, comandos e integração.",
        )
        self.login()

        urls = [
            reverse("technical_portal:home"),
            reverse("technical_portal:service-order-create"),
            reverse("technical_portal:service-orders"),
            reverse("technical_portal:service-order-detail", args=[order.pk]),
            reverse("technical_portal:assets"),
            reverse("technical_portal:search"),
            reverse("technical_portal:category-detail", args=[category.slug]),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

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
