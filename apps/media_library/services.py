"""Metadados de arquivo para assets de imagem."""

from __future__ import annotations

import mimetypes
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import MediaAsset


def gather_image_metadata(media_asset: MediaAsset) -> dict:
    """Retorna dict de campos do model a atualizar (sem salvar na instância)."""
    mf = getattr(media_asset, "image", None)
    if not mf or not getattr(mf, "name", None):
        return {}

    mime_type = (mimetypes.guess_type(mf.name)[0] or "")[:100]

    file_size = None
    try:
        file_size = mf.size
    except Exception:
        try:
            file_size = mf.storage.size(mf.name)
        except Exception:
            file_size = None

    updates: dict = {
        "file_size": file_size,
        "mime_type": mime_type,
        "width": None,
        "height": None,
    }

    try:
        abs_path = mf.path
    except Exception:
        abs_path = None

    if abs_path:
        try:
            from PIL import Image as PILImage

            with PILImage.open(abs_path) as im:
                w, h = im.size
                updates["width"] = int(w)
                updates["height"] = int(h)
                fmt = (im.format or "").upper()
                if fmt == "JPEG":
                    updates["mime_type"] = "image/jpeg"[:100]
                elif fmt == "PNG":
                    updates["mime_type"] = "image/png"[:100]
                elif fmt == "WEBP":
                    updates["mime_type"] = "image/webp"[:100]
        except Exception:
            pass

    return updates
