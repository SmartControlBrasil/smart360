from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.access_control_center.services.smart_system_access import bootstrap_smart_system_access
from apps.admin_shell.services.shell import get_technical_catalog_b2b_links


class TechnicalCatalogAdminAccessTests(TestCase):
    def setUp(self):
        bootstrap_smart_system_access()
        self.client = Client()
        user_model = get_user_model()
        self.superuser = user_model.objects.create_superuser(
            email="super.catalog@smart360.local",
            password="pwd123secure",
            first_name="Super",
            last_name="Catalog",
        )
        self.regular_user = user_model.objects.create_user(
            email="regular.catalog@smart360.local",
            password="pwd123secure",
            first_name="Regular",
            last_name="User",
        )

    def test_shell_links_point_to_admin_shell_routes(self):
        links = get_technical_catalog_b2b_links()

        self.assertIn("/dashboard/catalogo-tecnico/", links["manage_products"])
        self.assertIn("/dashboard/catalogo-tecnico/novo/", links["add_product"])
        self.assertIn("/dashboard/media/images/", links["media_library"])

    def test_superuser_accesses_manage_products(self):
        self.client.force_login(self.superuser)

        response = self.client.get(reverse("admin-shell:technical-catalog-product-list"))

        self.assertEqual(response.status_code, 200)

    def test_superuser_accesses_add_product(self):
        self.client.force_login(self.superuser)

        response = self.client.get(reverse("admin-shell:technical-catalog-product-create"))

        self.assertEqual(response.status_code, 200)

    def test_regular_user_without_staff_is_denied_on_manage_products(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("admin-shell:technical-catalog-product-list"))

        self.assertIn(response.status_code, {302, 403})
