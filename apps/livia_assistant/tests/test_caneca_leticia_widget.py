from django.test import TestCase, override_settings
from django.urls import reverse


class CanecaLeticiaWidgetTests(TestCase):
    @override_settings(LIVIA_ASSISTANT_ENABLED=False, CANECA_LETICIA_WIDGET_ENABLED=True)
    def test_simple_widget_when_ai_disabled(self):
        response = self.client.get(reverse("caneca_de_garagem:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-cdg-leticia-simple')
        self.assertContains(response, "Letícia")
        self.assertContains(response, "Quero personalizar uma caneca")
        self.assertNotContains(response, "data-livia-widget")

    @override_settings(LIVIA_ASSISTANT_ENABLED=True, CANECA_LETICIA_WIDGET_ENABLED=True)
    def test_chat_widget_when_ai_enabled_branding_leticia(self):
        response = self.client.get(reverse("caneca_de_garagem:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-livia-widget")
        self.assertContains(response, "Letícia")
        self.assertNotContains(response, "data-cdg-leticia-simple")

    @override_settings(LIVIA_ASSISTANT_ENABLED=True, CANECA_LETICIA_WIDGET_ENABLED=False)
    def test_no_widget_when_flag_off(self):
        response = self.client.get(reverse("caneca_de_garagem:home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "data-livia-widget")
        self.assertNotContains(response, "data-cdg-leticia-simple")
