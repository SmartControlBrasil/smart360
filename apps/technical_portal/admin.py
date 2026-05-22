from django.contrib import admin

from .models import ErrorCode, TechnicalArticle, TechnicalCategory


@admin.register(TechnicalCategory)
class TechnicalCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "order", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")


@admin.register(TechnicalArticle)
class TechnicalArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "difficulty", "is_active", "updated_at")
    list_filter = ("category", "difficulty", "is_active")
    search_fields = ("title", "summary", "content", "tags", "category__name")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("category__order", "title")


@admin.register(ErrorCode)
class ErrorCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "category", "equipment_type", "brand", "model", "is_active")
    list_filter = ("category", "equipment_type", "brand", "is_active")
    search_fields = (
        "code",
        "title",
        "equipment_type",
        "brand",
        "model",
        "probable_cause",
        "recommended_action",
        "category__name",
    )
    ordering = ("category__order", "equipment_type", "code")
