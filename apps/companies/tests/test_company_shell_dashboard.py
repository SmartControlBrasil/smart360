"""Testes do CRUD minimo de tenants (Company) no Admin Shell."""

from django.test import TestCase
from django.urls import reverse

from apps.access_control_center.services.smart_system_access import assign_smart_system_role, bootstrap_smart_system_access
from apps.companies.models import Company, Membership
from tests.factories.core import CompanyFactory, MembershipFactory, UserFactory


class CompanyShellDashboardTests(TestCase):
    def setUp(self):
        bootstrap_smart_system_access()

    def test_superuser_creates_company_via_shell(self):
        user = UserFactory(is_superuser=True, is_staff=True, password="pass12345!")
        url = reverse("admin-shell:dashboard-company-create")
        self.client.force_login(user)
        self.assertEqual(Company.objects.count(), 0)

        response = self.client.post(
            url,
            {
                "name": "Tenant Alpha",
                "legal_name": "Tenant Alpha LTDA",
                "tax_id": "12.345.678/0001-90",
                "email": "contato@tenant-alpha.local",
                "phone_number": "+551140010001",
                "website": "https://tenant-alpha.local",
                "status": Company.Status.ACTIVE,
                "vincular_usuario_atual": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        company = Company.objects.get(name="Tenant Alpha")
        self.assertTrue(
            Membership.objects.filter(user=user, company=company, status=Membership.Status.ACTIVE).exists()
        )

    def test_superuser_sees_all_companies_in_shell_list(self):
        c1 = CompanyFactory(name="Bravo", slug="bravo")
        c2 = CompanyFactory(name="Charlie", slug="charlie")
        user = UserFactory(is_superuser=True, is_staff=True, password="pass12345!")
        self.client.force_login(user)
        resp = self.client.get(reverse("admin-shell:dashboard-companies"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, c1.name)
        self.assertContains(resp, c2.name)

    def test_member_sees_only_scoped_companies(self):
        mine = CompanyFactory(name="Minha SA", slug="minha-sa")
        other = CompanyFactory(name="Outra SA", slug="outra-sa")
        user = UserFactory(is_staff=True, password="pass12345!")
        MembershipFactory(user=user, company=mine, status=Membership.Status.ACTIVE)
        assign_smart_system_role(user, "maintenance-manager")
        self.client.force_login(user)

        resp = self.client.get(reverse("admin-shell:dashboard-companies"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, mine.name)
        self.assertNotContains(resp, other.name)

    def test_member_gets_404_for_company_outside_scope(self):
        mine = CompanyFactory(slug="scoped-one")
        other = CompanyFactory(slug="scoped-two")
        user = UserFactory(is_staff=True, password="pass12345!")
        MembershipFactory(user=user, company=mine)
        assign_smart_system_role(user, "maintenance-manager")
        self.client.force_login(user)

        resp = self.client.get(reverse("admin-shell:dashboard-company-detail", kwargs={"company_id": other.pk}))
        self.assertEqual(resp.status_code, 404)

    def test_user_without_membership_or_shell_privilege_gets_403_on_company_list(self):
        user = UserFactory(is_staff=True, password="pass12345!")
        CompanyFactory(slug="isolada")
        self.client.force_login(user)

        resp = self.client.get(reverse("admin-shell:dashboard-companies"))
        self.assertEqual(resp.status_code, 403)
