from django.test import TestCase
from django.urls import reverse


class CriticalInternalAuthenticationTests(TestCase):
    def assert_redirects_to_admin_login(self, url):
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith(f"/admin/login/?next={url}"))

    def test_admin_shell_dashboard_requires_authentication(self):
        self.assert_redirects_to_admin_login(reverse("admin-shell:dashboard-entry"))

    def test_operations_health_requires_authentication(self):
        self.assert_redirects_to_admin_login(reverse("admin-shell:operations-health"))

    def test_client_user_management_requires_authentication(self):
        self.assert_redirects_to_admin_login(reverse("admin-shell:client-portal-users"))

    def test_livia_internal_dashboard_requires_authentication(self):
        self.assert_redirects_to_admin_login(reverse("admin-shell:livia-dashboard"))

    def test_client_portal_requires_authentication(self):
        response = self.client.get(reverse("technical_portal:home"))

        self.assertRedirects(response, "/login/?next=/portal/", fetch_redirect_response=False)

    def test_api_me_requires_authentication(self):
        response = self.client.get(reverse("users-me"))

        self.assertIn(response.status_code, {401, 403})

    def test_ai_agent_manual_run_requires_authentication(self):
        response = self.client.post(reverse("ai-agent-manual-run"), {}, content_type="application/json")

        self.assertIn(response.status_code, {401, 403})
