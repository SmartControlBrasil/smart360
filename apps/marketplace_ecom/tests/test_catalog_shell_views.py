from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.access_control_center.services.smart_system_access import bootstrap_smart_system_access
from apps.marketplace_ecom.models import TechnicalProduct


def _shell_product(**kwargs):
    data = dict(
        title="Produto Shell CRUD",
        slug="produto-shell-crud-test",
        brand="Marca Shell",
        supplier_name="Fornecedor Shell",
        category="Automação",
        short_description="Resumo do produto no shell.",
        description="Descrição completa.",
        application_area="Indústria",
        is_active=True,
        is_featured=False,
        display_order=10,
    )
    data.update(kwargs)
    return TechnicalProduct.objects.create(**data)


class TechnicalCatalogShellAccessTests(TestCase):
    def setUp(self):
        bootstrap_smart_system_access()
        self.client = Client()
        user_model = get_user_model()
        self.superuser = user_model.objects.create_superuser(
            email="super.shell.catalog@smart360.local",
            password="pwd123secure",
            first_name="Super",
            last_name="Shell",
        )
        self.regular_user = user_model.objects.create_user(
            email="regular.shell.catalog@smart360.local",
            password="pwd123secure",
            first_name="Regular",
            last_name="Shell",
        )
        self.product = _shell_product()

    def test_superuser_accesses_product_list(self):
        self.client.force_login(self.superuser)

        response = self.client.get(reverse("admin-shell:technical-catalog-product-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Catálogo Técnico B2B")
        self.assertContains(response, self.product.title)

    def test_superuser_accesses_create_form(self):
        self.client.force_login(self.superuser)

        response = self.client.get(reverse("admin-shell:technical-catalog-product-create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Novo produto técnico")

    def test_superuser_accesses_product_detail(self):
        self.client.force_login(self.superuser)

        response = self.client.get(
            reverse("admin-shell:technical-catalog-product-detail", kwargs={"pk": self.product.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.title)

    def test_superuser_accesses_product_update(self):
        self.client.force_login(self.superuser)

        response = self.client.get(
            reverse("admin-shell:technical-catalog-product-update", kwargs={"pk": self.product.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Salvar alterações")

    def test_regular_user_is_denied_on_product_list(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("admin-shell:technical-catalog-product-list"))

        self.assertIn(response.status_code, {302, 403})

    def test_regular_user_is_denied_on_create_form(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("admin-shell:technical-catalog-product-create"))

        self.assertIn(response.status_code, {302, 403})


class TechnicalCatalogShellCrudTests(TestCase):
    def setUp(self):
        bootstrap_smart_system_access()
        self.client = Client()
        user_model = get_user_model()
        self.superuser = user_model.objects.create_superuser(
            email="super.shell.crud@smart360.local",
            password="pwd123secure",
            first_name="Super",
            last_name="Crud",
        )
        self.client.force_login(self.superuser)

    def test_create_product_via_shell_form(self):
        response = self.client.post(
            reverse("admin-shell:technical-catalog-product-create"),
            data={
                "title": "Novo via Shell",
                "slug": "novo-via-shell",
                "brand": "Marca Nova",
                "supplier_name": "Parceiro Nova",
                "category": "Sensores",
                "short_description": "Resumo criado pelo shell.",
                "description": "Descrição criada pelo shell.",
                "application_area": "Linha de produção",
                "product_type": "Sensor",
                "applications": "Linha 1\nLinha 2",
                "features": "Alta precisão",
                "tags": "b2b",
                "specs": "Alcance | 10 m",
                "catalog_image": "",
                "display_order": "3",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        product = TechnicalProduct.objects.get(slug="novo-via-shell")
        self.assertEqual(product.title, "Novo via Shell")
        self.assertEqual(product.metadata.get("applications"), ["Linha 1", "Linha 2"])

    def test_update_product_via_shell_form(self):
        product = _shell_product(slug="editar-via-shell", title="Antes da edição")

        response = self.client.post(
            reverse("admin-shell:technical-catalog-product-update", kwargs={"pk": product.pk}),
            data={
                "title": "Depois da edição",
                "slug": product.slug,
                "brand": product.brand,
                "supplier_name": product.supplier_name,
                "category": product.category,
                "short_description": product.short_description,
                "description": product.description,
                "application_area": product.application_area,
                "product_type": "Atualizado",
                "applications": "",
                "features": "",
                "tags": "",
                "specs": "",
                "catalog_image": "",
                "display_order": "12",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(product.title, "Depois da edição")
        self.assertEqual(product.display_order, 12)
