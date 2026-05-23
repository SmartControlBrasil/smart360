from django.conf import settings
from django.db import models

from .services import gather_image_metadata

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


class MediaAsset(models.Model):
    """Imagem cadastrável no Admin Shell para reutilização posterior."""

    title = models.CharField("título", max_length=180)
    image = models.ImageField(
        "imagem",
        upload_to="media_library/images/%Y/%m/",
        blank=False,
        null=False,
    )
    alt_text = models.CharField("texto alternativo", max_length=255, blank=True)
    file_size = models.PositiveIntegerField(null=True, blank=True, editable=False)
    mime_type = models.CharField(max_length=100, blank=True, editable=False)
    width = models.PositiveIntegerField(null=True, blank=True, editable=False)
    height = models.PositiveIntegerField(null=True, blank=True, editable=False)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="enviado por",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="media_library_assets",
    )
    is_active = models.BooleanField("ativa", default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "imagem na biblioteca"
        verbose_name_plural = "imagens na biblioteca"

    def sync_metadata_after_save(self) -> None:
        """Atualiza metadados persistidos conforme arquivo salvo."""
        if not self.pk:
            return
        image_field = getattr(self, "image", None)
        if not image_field or not getattr(image_field, "name", None):
            return
        blob = gather_image_metadata(self)
        stale = []
        for field_name, value in blob.items():
            prev = getattr(self, field_name, None)
            if prev != value:
                setattr(self, field_name, value)
                stale.append(field_name)
        if stale:
            kw = {k: getattr(self, k) for k in stale}
            self.__class__.objects.filter(pk=self.pk).update(**kw)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.image and self.pk:
            self.sync_metadata_after_save()

    def human_file_size(self) -> str:
        if self.file_size is None:
            return "—"
        n = int(self.file_size)
        for unit, div in [("MB", 1 << 20), ("KB", 1 << 10)]:
            if n >= div:
                return f"{n / div:.1f} {unit}".replace(".0 ", " ")
        return f"{n} B"
