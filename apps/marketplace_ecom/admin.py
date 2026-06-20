from django.contrib import admin

from apps.marketplace_ecom.forms import TechnicalProductAdminForm
from apps.marketplace_ecom.models import TechnicalProduct


@admin.register(TechnicalProduct)
class TechnicalProductAdmin(admin.ModelAdmin):
    form = TechnicalProductAdminForm
    list_display = (
        "title",
        "slug",
        "brand",
        "category",
        "display_order",
        "is_active",
        "is_featured",
        "updated_at",
    )
    list_editable = ("display_order", "is_active", "is_featured")
    list_filter = ("is_active", "is_featured", "category", "brand")
    search_fields = (
        "title",
        "slug",
        "brand",
        "supplier_name",
        "category",
        "short_description",
        "description",
    )
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("featured_image",)
    ordering = ("display_order", "-is_featured", "-updated_at")
    fieldsets = (
        (
            "Identificação",
            {
                "fields": (
                    "title",
                    "slug",
                    "brand",
                    "supplier_name",
                    "category",
                    "product_type",
                ),
            },
        ),
        (
            "Conteúdo",
            {
                "fields": (
                    "short_description",
                    "description",
                    "application_area",
                    "applications",
                    "features",
                    "tags",
                    "specs",
                ),
            },
        ),
        (
            "Mídia e exibição",
            {
                "fields": (
                    "featured_image",
                    "catalog_image",
                    "display_order",
                    "is_featured",
                    "is_active",
                ),
            },
        ),
    )
