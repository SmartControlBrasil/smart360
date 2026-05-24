"""Unidade principal (OperationalSite) criada ao cadastro de cliente operacional."""

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.smart_system.models import MaintenanceClient, OperationalSite
from apps.smart_system.services.default_operational_site import (
    DEFAULT_PRINCIPAL_SITE_NAME,
    ensure_default_operational_site_for_client,
)
from tests.factories.core import CompanyFactory, MembershipFactory, UserFactory
from tests.factories.smart_system import MaintenanceClientFactory, OperationalSiteFactory


class EnsureDefaultOperationalSiteTests(TestCase):
    def test_creates_site_when_missing(self):
        company = CompanyFactory()
        client = MaintenanceClient.objects.create(
            company=company,
            display_name="Cliente X",
            contact_name="Fulano",
            contact_phone="+5511999998888",
        )
        site, created = ensure_default_operational_site_for_client(client)
        self.assertTrue(created)
        self.assertEqual(site.maintenance_client_id, client.id)
        self.assertEqual(site.name, DEFAULT_PRINCIPAL_SITE_NAME)
        self.assertEqual(site.contact_name, "Fulano")
        self.assertEqual(site.contact_phone, "+5511999998888")

    def test_idempotent_when_site_exists(self):
        company = CompanyFactory()
        client = MaintenanceClient.objects.create(company=company, display_name="Cliente Y")
        first, created1 = ensure_default_operational_site_for_client(client)
        _, created2 = ensure_default_operational_site_for_client(client)
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(OperationalSite.objects.filter(maintenance_client=client).count(), 1)
        self.assertEqual(first.pk, OperationalSite.objects.get(maintenance_client=client).pk)

    def test_no_second_principal_when_client_has_other_site(self):
        company = CompanyFactory()
        client = MaintenanceClient.objects.create(company=company, display_name="Cliente Z")
        OperationalSite.objects.create(maintenance_client=client, name="Filial norte", code="N")
        _, created = ensure_default_operational_site_for_client(client)
        self.assertFalse(created)


class MaintenanceClientCreatesPrincipalSiteShellIntegrationTests(TestCase):
    """Fluxo POST /smart-system/customers/new/ pelo Admin Shell."""

    def setUp(self):
        bootstrap_smart_system_access()
        user = UserFactory(is_staff=True, password="StrongPass!")
        company = CompanyFactory(slug="alpha-principal")
        MembershipFactory(user=user, company=company)
        assign_smart_system_role(user, "maintenance-manager")
        self.user = user
        self.company = company

    def test_post_creates_operational_site_and_message(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("admin-shell:smart-system-customer-create"),
            {
                "display_name": "Gym Alfa",
                "document_number": "10.020.030/0001-55",
                "contact_email": "alfa@gym.local",
                "contact_phone": "+5511988887766",
                "is_active": "on",
                "notes": "",
            },
            follow=False,
        )
        self.assertEqual(resp.status_code, 302)
        mc = MaintenanceClient.objects.get(display_name="Gym Alfa")
        site = OperationalSite.objects.get(maintenance_client=mc)
        self.assertEqual(site.name, DEFAULT_PRINCIPAL_SITE_NAME)
        self.assertEqual(mc.company_id, self.company.id)
        msgs = " ".join(str(m.message) for m in get_messages(resp.wsgi_request))
        self.assertIn("Cliente cadastrado com sucesso", msgs)
        self.assertIn("Unidade principal criada automaticamente", msgs)

    def test_inspection_routine_form_lists_auto_site_other_tenant_excluded(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("admin-shell:smart-system-customer-create"),
            {
                "display_name": "Cliente escopo local",
                "document_number": "",
                "contact_email": "loc@example.com",
                "contact_phone": "",
                "is_active": "on",
                "notes": "",
            },
        )
        ours = OperationalSite.objects.get(maintenance_client__display_name="Cliente escopo local")
        alien_company = CompanyFactory(slug="beta-alien-site")
        alien_client = MaintenanceClientFactory(
            company=alien_company,
            display_name="Cliente outro tenant formulário rotina",
        )
        OperationalSiteFactory(
            maintenance_client=alien_client,
            name="UNIDADE-RIVAL-X9",
            code="ALIEN",
        )
        rq = self.client.get(reverse("admin-shell:smart-system-inspection-routine-create"))
        self.assertEqual(rq.status_code, 200)
        self.assertContains(rq, ours.name)
        self.assertNotContains(rq, "UNIDADE-RIVAL-X9")
