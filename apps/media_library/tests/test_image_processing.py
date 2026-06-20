from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.media_library.models import MediaAsset
from apps.media_library.services.image_processing import optimize_image


def make_image_upload(size=(800, 600), mode="RGB", image_format="PNG"):
    output = BytesIO()
    color = (30, 90, 180, 180) if mode == "RGBA" else (30, 90, 180)
    Image.new(mode, size, color=color).save(output, format=image_format)
    return SimpleUploadedFile(
        "original.png",
        output.getvalue(),
        content_type="image/png",
    )


class OptimizeImageTests(TestCase):
    def setUp(self):
        self.media_dir = TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.media_dir.name)
        self.override.enable()

    def tearDown(self):
        self.override.disable()
        self.media_dir.cleanup()

    def test_original_upload_generates_processed_webp_and_done_status(self):
        asset = MediaAsset.objects.create(
            title="Imagem de produto",
            original_file=make_image_upload(),
        )

        optimize_image(asset)
        asset.refresh_from_db()

        self.assertTrue(asset.original_file.name.endswith(".png"))
        self.assertTrue(asset.processed_file.name.endswith(".webp"))
        self.assertTrue(asset.processed_file.storage.exists(asset.processed_file.name))
        self.assertEqual(asset.processing_status, MediaAsset.ProcessingStatus.DONE)
        self.assertEqual((asset.width, asset.height), (800, 600))

        with asset.processed_file.open("rb") as processed:
            with Image.open(processed) as image:
                self.assertEqual(image.format, "WEBP")

    def test_reduces_width_to_1600_preserving_aspect_ratio(self):
        asset = MediaAsset.objects.create(
            title="Imagem larga",
            original_file=make_image_upload(size=(2400, 1200)),
        )

        optimize_image(asset)
        asset.refresh_from_db()

        self.assertEqual(asset.width, 1600)
        self.assertEqual(asset.height, 800)
        self.assertEqual(asset.processing_status, MediaAsset.ProcessingStatus.DONE)
