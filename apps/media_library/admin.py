from django.contrib import admin

from .models import MediaAsset


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "mime_type", "file_size", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "alt_text")
    readonly_fields = (
        "created_at",
        "updated_at",
        "uploaded_by",
        "file_size",
        "mime_type",
        "width",
        "height",
    )
