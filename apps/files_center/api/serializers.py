from rest_framework import serializers

from ..models import (
    FileAccessLog,
    FileCategory,
    FileCollection,
    FileCollectionItem,
    FileLink,
    FileVersion,
    MediaAsset,
    StoredFile,
)
from ..services.files_service import FileLinkService, StoredFileService


class FileCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FileCategory
        fields = ("id", "public_id", "name", "slug", "description", "is_active", "ordering", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class StoredFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoredFile
        fields = (
            "id",
            "public_id",
            "original_name",
            "stored_name",
            "file",
            "mime_type",
            "extension",
            "size_bytes",
            "category",
            "storage_backend",
            "checksum",
            "visibility",
            "is_active",
            "uploaded_by",
            "uploaded_at",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "stored_name", "extension", "size_bytes", "checksum", "created_at", "updated_at")

    def create(self, validated_data):
        return StoredFileService.create_file(**validated_data)


class FileLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileLink
        fields = (
            "id",
            "public_id",
            "stored_file",
            "related_module",
            "related_item_type",
            "related_item_id",
            "relation_type",
            "is_primary",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "created_at", "updated_at")

    def create(self, validated_data):
        return FileLinkService.create_link(**validated_data)


class MediaAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = MediaAsset
        fields = ("id", "public_id", "stored_file", "asset_type", "title", "alt_text", "caption", "ordering", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class FileVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileVersion
        fields = ("id", "public_id", "parent_file", "stored_file", "version_label", "created_at", "created_by", "notes", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class FileAccessLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAccessLog
        fields = ("id", "public_id", "stored_file", "accessed_by", "action_type", "ip_address", "user_agent", "accessed_at", "created_at")
        read_only_fields = fields


class FileCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileCollection
        fields = ("id", "public_id", "name", "slug", "description", "collection_type", "created_by", "is_active", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class FileCollectionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileCollectionItem
        fields = ("id", "public_id", "collection", "stored_file", "ordering", "is_primary", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "updated_at")

