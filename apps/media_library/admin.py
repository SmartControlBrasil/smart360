from django.contrib import admin

from .models import MediaAsset


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("title", "asset_type", "processing_status", "is_active", "mime_type", "file_size", "created_at")
    list_filter = ("asset_type", "processing_status", "is_active")
    search_fields = ("title", "alt_text")
    readonly_fields = (
        "created_at",
        "updated_at",
        "uploaded_by",
        "processed_file",
        "file_size",
        "mime_type",
        "width",
        "height",
    )
