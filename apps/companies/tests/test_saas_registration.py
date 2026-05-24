"""
Fluxo publico de cadastro SaaS: empresa + usuario administrador inicial.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.access_control_center.services.smart_system_access import bootstrap_smart_system_access
from apps.companies.models import Company, Membership
from tests.factories.core import CompanyFactory


User = get_user_model()


def _valid_signup_payload(**overrides):
    base = {
        "company_name": "Minha Industria SA",
        "legal_name": "Minha Industria SA",
        "tax_id": "12.345.678/0001-99",
        "company_email": "contato@minhaindustria.com",
        "phone_number": "+5511999887766",
        "website": "https://minhaindustria.com",
        "city": "Campinas",
        "state": "SP",
        "admin_name": "Ana Souza",
        "admin_email": "ana@minhaindustria.com",
        "password1": "StrongPass123!",
        "password2": "StrongPass123!",
    }
    base.update(overrides)
    return base


class SaasTenantRegistrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        bootstrap_smart_system_access()

    def test_get_signup_returns_200(self):
        response = self.client.get(reverse("users:saas-register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Criar conta empresarial")

    def test_login_page_links_to_signup(self):
        response = self.client.get(reverse("users:login"))
        self.assertContains(response, reverse("users:saas-register"))
        self.assertContains(response, "Cadastrar minha empresa")

    def test_valid_signup_creates_records_and_logs_in(self):
        before_company = Company.objects.count()
        before_user = User.objects.count()
        payload = _valid_signup_payload()
        response = self.client.post(reverse("users:saas-register"), data=payload, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/ecossistema/")
        self.assertEqual(Company.objects.count(), before_company + 1)
        self.assertEqual(User.objects.count(), before_user + 1)

        company = Company.objects.get(name=payload["company_name"])
        user = User.objects.get(email=payload["admin_email"])
        self.assertTrue(Membership.objects.filter(user=user, company=company, is_primary=True).exists())
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(user.pk))

        self.client.get("/ecossistema/")
        session = self.client.session
        self.assertEqual(session["smart_system_active_company_id"], company.id)

    def test_signup_user_can_login_explicitly(self):
        payload = _valid_signup_payload(admin_email="explicit@empresa.com")
        self.client.post(reverse("users:saas-register"), data=payload, follow=False)
        self.client.logout()
        login_response = self.client.post(
            reverse("users:login"),
            {"username": "explicit@empresa.com", "password": payload["password1"]},
            follow=False,
        )
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(login_response["Location"], "/ecossistema/")

    def test_after_signup_single_membership_sees_only_own_until_invited(self):
        """Cenario real pos-cadastro: somente a Company criada pelo fluxo."""
        payload = _valid_signup_payload(admin_email="onlyone@empresa.com")
        self.client.post(reverse("users:saas-register"), data=payload, follow=False)
        user = User.objects.get(email="onlyone@empresa.com")
        from apps.companies.services.tenant_scope import TenantScopeService

        companies = TenantScopeService.get_available_companies(user)
        self.assertEqual(len(companies), 1)
        self.assertEqual(companies[0].name, payload["company_name"])

    def test_duplicate_admin_email_returns_error_no_side_effects(self):
        payload_a = _valid_signup_payload(admin_email="dup@dup.com")
        self.client.post(reverse("users:saas-register"), data=payload_a)

        snap_c = Company.objects.count()
        snap_u = User.objects.count()
        self.client.logout()
        payload_b = _valid_signup_payload(
            company_name="Outro Nome SA",
            admin_email="dup@dup.com",
            tax_id="98.765.432/0001-10",
        )
        response = self.client.post(reverse("users:saas-register"), data=payload_b)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ja existe uma conta com este e-mail")
        self.assertEqual(Company.objects.count(), snap_c)
        self.assertEqual(User.objects.count(), snap_u)

    def test_password_mismatch_no_persist(self):
        snap_c = Company.objects.count()
        snap_u = User.objects.count()
        payload = _valid_signup_payload(
            admin_email="mismatch@empresa.com",
            password1="StrongPass123!",
            password2="StrongPass999!",
        )
        response = self.client.post(reverse("users:saas-register"), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "As senhas nao coincidem")
        self.assertEqual(Company.objects.count(), snap_c)
        self.assertEqual(User.objects.count(), snap_u)

    def test_empty_company_name_rejected(self):
        payload = _valid_signup_payload(company_name="   ")
        response = self.client.post(reverse("users:saas-register"), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Informe o nome da empresa")

    def test_duplicate_tax_id_blocked(self):
        CompanyFactory(name="Existente", slug="existente-tax", tax_id="11.111.111/1111-11")
        before = Company.objects.count()
        payload = _valid_signup_payload(
            company_name="Nova Empresa Tentando Doc",
            tax_id="11111111111111",
            admin_email="tax@nova.com",
        )
        response = self.client.post(reverse("users:saas-register"), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ja existe uma empresa cadastrada com este documento")
        self.assertEqual(Company.objects.count(), before)
        self.assertFalse(User.objects.filter(email="tax@nova.com").exists())
