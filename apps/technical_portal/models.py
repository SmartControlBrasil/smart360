from django.db import models


class TechnicalCategory(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)
    icon_name = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "categoria técnica"
        verbose_name_plural = "categorias técnicas"

    def __str__(self):
        return self.name


class TechnicalArticle(models.Model):
    class Difficulty(models.TextChoices):
        BASIC = "basic", "Básico"
        INTERMEDIATE = "intermediate", "Intermediário"
        ADVANCED = "advanced", "Avançado"

    category = models.ForeignKey(
        TechnicalCategory,
        on_delete=models.PROTECT,
        related_name="articles",
    )
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True)
    summary = models.TextField()
    content = models.TextField()
    tags = models.CharField(max_length=255, blank=True)
    difficulty = models.CharField(
        max_length=20,
        choices=Difficulty.choices,
        default=Difficulty.BASIC,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category__order", "title"]
        verbose_name = "artigo técnico"
        verbose_name_plural = "artigos técnicos"

    def __str__(self):
        return self.title


class ErrorCode(models.Model):
    category = models.ForeignKey(
        TechnicalCategory,
        on_delete=models.PROTECT,
        related_name="error_codes",
    )
    equipment_type = models.CharField(max_length=120)
    brand = models.CharField(max_length=120, blank=True)
    model = models.CharField(max_length=120, blank=True)
    code = models.CharField(max_length=60)
    title = models.CharField(max_length=180)
    probable_cause = models.TextField()
    recommended_action = models.TextField()
    safety_warning = models.TextField(blank=True)
    source_note = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category__order", "equipment_type", "code"]
        verbose_name = "código de erro"
        verbose_name_plural = "códigos de erro"

    def __str__(self):
        return f"{self.code} - {self.title}"
