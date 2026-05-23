from django.contrib import admin

from apps.marketplace_ecom.models import TechnicalProduct


@admin.register(TechnicalProduct)
class TechnicalProductAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "slug",
        "brand",
        "category",
        "is_active",
        "is_featured",
        "updated_at",
    )
    list_filter = ("is_active", "is_featured", "category", "brand")
    search_fields = ("title", "slug", "brand", "supplier_name", "category", "short_description")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("featured_image",)
    ordering = ("-is_featured", "-updated_at")
