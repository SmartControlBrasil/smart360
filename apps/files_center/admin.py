from django.contrib import admin

from .models import (
    FileAccessLog,
    FileCategory,
    FileCollection,
    FileCollectionItem,
    FileLink,
    FileVersion,
    MediaAsset,
    StoredFile,
)


class FileCollectionItemInline(admin.TabularInline):
    model = FileCollectionItem
    extra = 0
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("stored_file",)


@admin.register(FileCategory)
class FileCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "ordering")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(StoredFile)
class StoredFileAdmin(admin.ModelAdmin):
    list_display = ("original_name", "mime_type", "category", "storage_backend", "visibility", "is_active", "uploaded_at")
    list_filter = ("category", "storage_backend", "visibility", "is_active")
    search_fields = ("original_name", "stored_name", "mime_type", "checksum")
    readonly_fields = ("public_id", "stored_name", "size_bytes", "uploaded_at", "created_at", "updated_at")
    autocomplete_fields = ("category", "uploaded_by")


@admin.register(FileLink)
class FileLinkAdmin(admin.ModelAdmin):
    list_display = ("stored_file", "related_module", "related_item_type", "related_item_id", "relation_type", "is_primary")
    list_filter = ("related_module", "relation_type", "is_primary")
    search_fields = ("related_module", "related_item_type", "related_item_id", "relation_type")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("stored_file",)


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ("stored_file", "asset_type", "title", "ordering", "is_active")
    list_filter = ("asset_type", "is_active")
    search_fields = ("title", "alt_text", "caption", "stored_file__original_name")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("stored_file",)


@admin.register(FileVersion)
class FileVersionAdmin(admin.ModelAdmin):
    list_display = ("parent_file", "stored_file", "version_label", "created_by", "created_at")
    list_filter = ("created_at",)
    search_fields = ("version_label", "notes", "parent_file__original_name", "stored_file__original_name")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("parent_file", "stored_file", "created_by")


@admin.register(FileAccessLog)
class FileAccessLogAdmin(admin.ModelAdmin):
    list_display = ("stored_file", "action_type", "accessed_by", "ip_address", "accessed_at")
    list_filter = ("action_type", "accessed_at")
    search_fields = ("stored_file__original_name", "ip_address", "user_agent")
    readonly_fields = ("public_id", "accessed_at", "created_at")
    autocomplete_fields = ("stored_file", "accessed_by")


@admin.register(FileCollection)
class FileCollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "collection_type", "created_by", "is_active", "created_at")
    list_filter = ("collection_type", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("created_by",)
    inlines = (FileCollectionItemInline,)


@admin.register(FileCollectionItem)
class FileCollectionItemAdmin(admin.ModelAdmin):
    list_display = ("collection", "stored_file", "ordering", "is_primary", "created_at")
    list_filter = ("collection", "is_primary")
    search_fields = ("collection__name", "stored_file__original_name")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("collection", "stored_file")
