from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class Smart360AuthViewTests(TestCase):
    def setUp(self):
        self.password = "StrongPass123"
        self.user = get_user_model().objects.create_user(
            email="tecnico@smart360.local",
            password=self.password,
            first_name="Tecnico",
        )

    def test_login_get_returns_200(self):
        response = self.client.get(reverse("users:login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Entrar")

    def test_login_links_to_saas_signup(self):
        response = self.client.get(reverse("users:login"))
        self.assertContains(response, reverse("users:saas-register"))
        self.assertContains(response, "Cadastrar minha empresa")

    def test_login_form_contains_csrf(self):
        response = self.client.get(reverse("users:login"))

        self.assertContains(response, "csrfmiddlewaretoken")

    def test_invalid_login_does_not_authenticate(self):
        response = self.client.post(
            reverse("users:login"),
            {"username": self.user.email, "password": "senha-errada"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "Não foi possível entrar")

    def test_valid_login_redirects(self):
        response = self.client.post(
            reverse("users:login"),
            {"username": self.user.email, "password": self.password},
        )

        self.assertRedirects(response, "/ecossistema/", fetch_redirect_response=False)
        self.assertEqual(str(self.client.session["_auth_user_id"]), str(self.user.pk))

    def test_password_reset_get_returns_200(self):
        response = self.client.get(reverse("users:password-reset"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recuperar senha")

    def test_logout_redirects_to_login(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("users:logout"))

        self.assertRedirects(response, reverse("users:login"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
