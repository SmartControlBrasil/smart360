"""Cadastro de cliente operacional (MaintenanceClient) com tenant / Company no Admin Shell."""

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.companies.models import Company
from apps.smart_system.models import MaintenanceClient
from tests.factories.core import CompanyFactory, MembershipFactory, UserFactory
from tests.factories.smart_system import MaintenanceClientFactory


class MaintenanceCustomerTenantShellTests(TestCase):
    def setUp(self):
        bootstrap_smart_system_access()

    def _member_with_company(self):
        user = UserFactory(is_staff=True, password="pass12345!")
        company = CompanyFactory(name="Operacional SA", slug="operacional-sa")
        MembershipFactory(user=user, company=company)
        assign_smart_system_role(user, "maintenance-manager")
        return user, company

    def test_member_creates_client_linked_to_company(self):
        user, company = self._member_with_company()
        self.client.force_login(user)
        url = reverse("admin-shell:smart-system-customer-create")

        resp = self.client.post(
            url,
            {
                "display_name": "Cliente Gym",
                "document_number": "11.222.333/0001-44",
                "contact_email": "contato@gym.local",
                "contact_phone": "+5511999990000",
                "is_active": "on",
                "notes": "",
            },
        )

        self.assertEqual(resp.status_code, 302)
        client = MaintenanceClient.objects.get(display_name="Cliente Gym")
        self.assertEqual(client.company_id, company.id)
        msgs = [m.message for m in get_messages(resp.wsgi_request)]
        self.assertTrue(any("Cliente cadastrado com sucesso." in str(m) for m in msgs))
        self.assertTrue(any("Unidade principal criada automaticamente" in str(m) for m in msgs))

    def test_customer_list_scoped_to_user_company(self):
        user, company = self._member_with_company()
        other_company = CompanyFactory(name="Rival", slug="rival-co")
        MaintenanceClientFactory(company=company, display_name="Cliente autorizado")
        MaintenanceClientFactory(company=other_company, display_name="Cliente outro tenant")

        self.client.force_login(user)
        resp = self.client.get(reverse("admin-shell:smart-system-customers"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Cliente autorizado")
        self.assertNotContains(resp, "Cliente outro tenant")

    def test_superuser_single_company_no_picker_binds_client(self):
        su = UserFactory(is_superuser=True, is_staff=True, password="pass12345!")
        tenant = CompanyFactory(slug="unico-tenant")
        self.client.force_login(su)

        resp = self.client.post(
            reverse("admin-shell:smart-system-customer-create"),
            {
                "display_name": "Cliente Solo",
                "document_number": "",
                "contact_email": "solo@test.local",
                "contact_phone": "",
                "is_active": "on",
                "notes": "",
            },
        )

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(MaintenanceClient.objects.get(display_name="Cliente Solo").company_id, tenant.id)

    def test_superuser_two_companies_must_post_tenant_choice(self):
        su = UserFactory(is_superuser=True, is_staff=True, password="pass12345!")
        alpha = CompanyFactory(name="Alpha Pick", slug="alpha-pick")
        beta = CompanyFactory(name="Beta Pick", slug="beta-pick")
        self.client.force_login(su)

        resp_bad = self.client.post(
            reverse("admin-shell:smart-system-customer-create"),
            {
                "display_name": "Sem tenant field",
                "document_number": "",
                "contact_email": "x@test.local",
                "contact_phone": "",
                "is_active": "on",
                "notes": "",
            },
        )
        self.assertEqual(resp_bad.status_code, 400)
        self.assertContains(resp_bad, "Este campo é obrigatório.", status_code=400)

        resp_ok = self.client.post(
            reverse("admin-shell:smart-system-customer-create"),
            {
                "display_name": "Com tenant",
                "document_number": "",
                "contact_email": "ok@test.local",
                "contact_phone": "",
                "is_active": "on",
                "notes": "",
                "saas_tenant_company": str(alpha.id),
            },
        )
        self.assertEqual(resp_ok.status_code, 302)
        self.assertEqual(MaintenanceClient.objects.get(display_name="Com tenant").company_id, alpha.id)

        self.assertFalse(MaintenanceClient.objects.filter(display_name="Sem tenant field").exists())

    def test_user_without_available_tenant_cannot_create_client(self):
        user = UserFactory(is_staff=True, password="pass12345!")
        assign_smart_system_role(user, "maintenance-manager")
        CompanyFactory(slug="some-tenant")
        self.client.force_login(user)

        resp = self.client.post(
            reverse("admin-shell:smart-system-customer-create"),
            {
                "display_name": "Sem membership",
                "document_number": "",
                "contact_email": "n@m.local",
                "contact_phone": "",
                "is_active": "on",
                "notes": "",
            },
        )

        self.assertEqual(resp.status_code, 403)
        self.assertContains(resp, "Nenhuma empresa vinculada", status_code=403)
        self.assertFalse(MaintenanceClient.objects.filter(display_name="Sem membership").exists())
