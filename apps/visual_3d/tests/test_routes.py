from django.conf import settings
from django.test import SimpleTestCase, override_settings


TEST_MIDDLEWARE = [
    mw
    for mw in settings.MIDDLEWARE
    if mw != "shared_kernel.observability.middleware.CorrelationIdMiddleware"
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class Visual3DRouteDisabledTests(SimpleTestCase):
    def test_visual_3d_public_routes_are_not_exposed(self):
        for path in ("/visual-3d/demo/", "/visual-3d/editor-2d/"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
