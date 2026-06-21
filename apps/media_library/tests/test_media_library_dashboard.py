from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.access_control_center.services.smart_system_access import bootstrap_smart_system_access
from apps.media_library.models import MediaAsset


def _make_jpeg_bytes(name_hint="blob", size_px=(120, 80)):
    buf = BytesIO()
    img = Image.new("RGB", size_px, color=(40, 80, 200))
    img.save(buf, format="JPEG")
    buf.seek(0)
    setattr(buf, "name", f"{name_hint}.jpg")
    return buf.read()


@override_settings(
    MEDIA_ROOT="/tmp/smart360-media-library-test-media",
)
class MediaLibraryDashboardTests(TestCase):
    def setUp(self):
        bootstrap_smart_system_access()
        self.client = Client()
        user_model = get_user_model()
        self.super_user = user_model.objects.create_superuser(
            email="super@media.example.com",
            password="pwd123secure",
            first_name="Super",
            last_name="User",
        )
        self.regular_user = user_model.objects.create_user(
            email="regular@media.example.com",
            password="pwd123secure",
            first_name="Regular",
            last_name="User",
        )

    def _login_super(self):
        self.client.force_login(self.super_user)

    def test_superuser_accesses_media_library_list(self):
        self._login_super()

        response = self.client.get(reverse("admin-shell:media-image-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Biblioteca de imagens")

    def test_superuser_accesses_image_upload_page(self):
        self._login_super()

        response = self.client.get(reverse("admin-shell:media-image-upload"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enviar imagem")

    def test_regular_user_without_permission_is_denied_on_upload(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("admin-shell:media-image-upload"))

        self.assertContains(response, "Acesso negado", status_code=403)

    def test_upload_valid_creates_asset(self):
        self._login_super()
        jpeg_content = _make_jpeg_bytes()
        rsp_ok = self.client.post(
            reverse("admin-shell:media-image-upload"),
            {
                "title": "Imagem equipamento",
                "alt_text": "Detalhe",
                "is_active": "1",
                "original_file": (BytesIO(jpeg_content), "foto-demo.jpg"),
            },
        )
        self.assertEqual(rsp_ok.status_code, 302)
        asset = MediaAsset.objects.get(title="Imagem equipamento")
        self.assertTrue(asset.original_file.name.endswith(".jpg"))
        self.assertEqual(asset.uploaded_by_id, self.super_user.id)
        self.assertIsNotNone(asset.file_size)
        self.assertGreater(asset.file_size or 0, 0)
        self.assertIsNotNone(asset.width)
        self.assertIsNotNone(asset.height)

    def test_upload_rejects_invalid_extension(self):
        self._login_super()
        rsp = self.client.post(
            reverse("admin-shell:media-image-upload"),
            {
                "title": "Ícone svg",
                "is_active": "1",
                "original_file": (BytesIO(b"<svg></svg>"), "evil.svg"),
            },
        )
        self.assertEqual(rsp.status_code, 400)
        self.assertEqual(MediaAsset.objects.filter(title="Ícone svg").count(), 0)

    def test_upload_rejects_oversized_file(self):
        self._login_super()
        oversized = BytesIO(b"x" * (5 * 1024 * 1024 + 1))
        rsp = self.client.post(
            reverse("admin-shell:media-image-upload"),
            {
                "title": "Arquivo grande",
                "is_active": "1",
                "original_file": (oversized, "big.jpg"),
            },
        )
        self.assertEqual(rsp.status_code, 400)
        self.assertEqual(MediaAsset.objects.filter(title="Arquivo grande").count(), 0)

    def test_list_default_shows_only_active_with_filters(self):
        self._login_super()
        self.client.post(
            reverse("admin-shell:media-image-upload"),
            {
                "title": "Asset ativo",
                "is_active": "1",
                "original_file": (BytesIO(_make_jpeg_bytes("one")), "a.jpg"),
            },
        )
        self.client.post(
            reverse("admin-shell:media-image-upload"),
            {
                "title": "Asset inativo",
                "is_active": "1",
                "original_file": (BytesIO(_make_jpeg_bytes("two")), "b.jpg"),
            },
        )
        inactive_pk = MediaAsset.objects.get(title="Asset inativo").pk
        self.client.post(reverse("admin-shell:media-image-deactivate", kwargs={"pk": inactive_pk}))
        rsp_active = self.client.get(reverse("admin-shell:media-image-list"))
        self.assertEqual(rsp_active.status_code, 200)
        content = rsp_active.content.decode()
        self.assertIn("Asset ativo", content)
        self.assertNotIn("Asset inativo", content)
        rsp_all = self.client.get(reverse("admin-shell:media-image-list"), {"status": "all"})
        self.assertIn("Asset inativo", rsp_all.content.decode())
        rsp_inactive = self.client.get(reverse("admin-shell:media-image-list"), {"status": "inactive"})
        self.assertIn("Asset inativo", rsp_inactive.content.decode())

    def test_detail_edit_deactivate_metadata_display(self):
        self._login_super()
        jpeg = _make_jpeg_bytes()
        self.client.post(
            reverse("admin-shell:media-image-upload"),
            {
                "title": "Bomba hidráulica",
                "alt_text": "Bomba",
                "is_active": "1",
                "original_file": (BytesIO(jpeg), "bomba.jpg"),
            },
        )
        pk = MediaAsset.objects.get(title="Bomba hidráulica").pk
        asset = MediaAsset.objects.get(pk=pk)
        asset.metadata = {"campaign": "v1"}
        asset.save(update_fields=["metadata"])

        detail_rsp = self.client.get(reverse("admin-shell:media-image-detail", kwargs={"pk": pk}))
        self.assertEqual(detail_rsp.status_code, 200)
        self.assertIn(b"v1", detail_rsp.content)

        rsp_edit = self.client.post(
            reverse("admin-shell:media-image-edit", kwargs={"pk": pk}),
            {
                "title": "Pump revisado",
                "alt_text": "Nova descrição",
                "is_active": "1",
            },
        )
        self.assertEqual(rsp_edit.status_code, 302)
        refreshed = MediaAsset.objects.get(pk=pk)
        self.assertEqual(refreshed.title, "Pump revisado")
        self.assertEqual(refreshed.alt_text, "Nova descrição")

        self.client.post(reverse("admin-shell:media-image-deactivate", kwargs={"pk": pk}))
        self.assertFalse(MediaAsset.objects.get(pk=pk).is_active)

    @patch("apps.media_library.dashboard_views.remove_background")
    def test_detail_exposes_remove_background_action(self, mocked_remove_background):
        self._login_super()
        asset = MediaAsset.objects.create(
            title="Produto para recorte",
            original_file=ContentFile(_make_jpeg_bytes(), name="produto.jpg"),
        )

        detail = self.client.get(reverse("admin-shell:media-image-detail", kwargs={"pk": asset.pk}))
        self.assertContains(detail, "Remover fundo")

        response = self.client.post(
            reverse("admin-shell:media-image-remove-background", kwargs={"pk": asset.pk})
        )

        self.assertEqual(response.status_code, 302)
        mocked_remove_background.assert_called_once()
