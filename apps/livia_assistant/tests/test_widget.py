from django.test import override_settings, TestCase
from django.urls import reverse


class LiviaWidgetRenderingTests(TestCase):
    @override_settings(LIVIA_ASSISTANT_ENABLED=False)
    def test_widget_does_not_render_when_disabled(self):
        response = self.client.get(reverse("institutional:home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "data-livia-widget")

    @override_settings(LIVIA_ASSISTANT_ENABLED=True)
    def test_widget_renders_when_enabled(self):
        response = self.client.get(reverse("institutional:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-livia-widget")
        self.assertContains(response, "Fale com a Lívia")
