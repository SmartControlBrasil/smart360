from django.conf import settings
from django.db import models


class TechnicalProduct(models.Model):
    """Produto do catálogo técnico (persistente). Imagens opcionais via biblioteca."""

    title = models.CharField("título", max_length=220)
    slug = models.SlugField("slug", max_length=220, unique=True, db_index=True)
    brand = models.CharField("fabricante/marca", max_length=120)
    supplier_name = models.CharField("nome do fornecedor/parceiro", max_length=180)
    category = models.CharField("categoria", max_length=120)
    short_description = models.CharField("resumo curto", max_length=500)
    description = models.TextField("descrição completa", blank=True)
    application_area = models.CharField("área de aplicação", max_length=300)
    featured_image = models.ForeignKey(
        "media_library.MediaAsset",
        verbose_name="imagem destacada",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="technical_products_featured",
    )
    is_active = models.BooleanField("ativo no catálogo", default=True, db_index=True)
    is_featured = models.BooleanField("destacar na home", default=False, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-is_featured", "-updated_at")
        verbose_name = "produto técnico"
        verbose_name_plural = "produtos técnicos do catálogo"

    def __str__(self) -> str:
        return self.title
