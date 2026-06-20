"""Otimização de imagens da biblioteca de mídia."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image, ImageOps

from apps.media_library.models import MediaAsset

MAX_WIDTH = 1600
WEBP_QUALITY = 85


def _target_mode(image: Image.Image) -> str:
    has_alpha = image.mode in {"RGBA", "LA"} or (
        image.mode == "P" and "transparency" in image.info
    )
    return "RGBA" if has_alpha else "RGB"


def optimize_image(asset: MediaAsset) -> MediaAsset:
    """Gera a versão WEBP otimizada do arquivo original de um asset."""
    if not asset.pk:
        raise ValueError("O asset precisa estar salvo antes do processamento.")
    if not asset.original_file or not asset.original_file.name:
        raise ValueError("O asset não possui arquivo original.")

    MediaAsset.objects.filter(pk=asset.pk).update(
        processing_status=MediaAsset.ProcessingStatus.PROCESSING,
        processing_notes="",
        updated_at=timezone.now(),
    )
    asset.processing_status = MediaAsset.ProcessingStatus.PROCESSING
    asset.processing_notes = ""

    try:
        with asset.original_file.open("rb") as source:
            with Image.open(source) as opened:
                image = ImageOps.exif_transpose(opened)
                image.load()
                image = image.convert(_target_mode(image))

        if image.width > MAX_WIDTH:
            target_height = max(1, round(image.height * MAX_WIDTH / image.width))
            image = image.resize((MAX_WIDTH, target_height), Image.Resampling.LANCZOS)

        output = BytesIO()
        image.save(
            output,
            format="WEBP",
            quality=WEBP_QUALITY,
            method=6,
        )
        output.seek(0)

        source_stem = Path(asset.original_file.name).stem
        filename = f"{source_stem}-{asset.pk}.webp"
        asset.processed_file.save(filename, ContentFile(output.read()), save=False)

        asset.width, asset.height = image.size
        asset.processing_status = MediaAsset.ProcessingStatus.DONE
        asset.processing_notes = ""
        MediaAsset.objects.filter(pk=asset.pk).update(
            processed_file=asset.processed_file.name,
            width=asset.width,
            height=asset.height,
            processing_status=asset.processing_status,
            processing_notes=asset.processing_notes,
            updated_at=timezone.now(),
        )
        return asset
    except Exception as exc:
        asset.processing_status = MediaAsset.ProcessingStatus.FAILED
        asset.processing_notes = str(exc)
        MediaAsset.objects.filter(pk=asset.pk).update(
            processing_status=asset.processing_status,
            processing_notes=asset.processing_notes,
            updated_at=timezone.now(),
        )
        raise
