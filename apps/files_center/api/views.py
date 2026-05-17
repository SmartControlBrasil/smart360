from rest_framework import permissions, viewsets

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
from .serializers import (
    FileAccessLogSerializer,
    FileCategorySerializer,
    FileCollectionItemSerializer,
    FileCollectionSerializer,
    FileLinkSerializer,
    FileVersionSerializer,
    MediaAssetSerializer,
    StoredFileSerializer,
)


class FilesCenterBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class FileCategoryViewSet(FilesCenterBaseViewSet):
    queryset = FileCategory.objects.all()
    serializer_class = FileCategorySerializer
    filterset_fields = ("is_active",)
    search_fields = ("name", "slug", "description")
    ordering_fields = ("ordering", "name", "updated_at")


class StoredFileViewSet(FilesCenterBaseViewSet):
    queryset = StoredFile.objects.select_related("category", "uploaded_by").all()
    serializer_class = StoredFileSerializer
    filterset_fields = ("category", "storage_backend", "visibility", "is_active", "uploaded_by")
    search_fields = ("original_name", "stored_name", "mime_type", "checksum")
    ordering_fields = ("uploaded_at", "created_at", "size_bytes", "updated_at")


class FileLinkViewSet(FilesCenterBaseViewSet):
    queryset = FileLink.objects.select_related("stored_file").all()
    serializer_class = FileLinkSerializer
    filterset_fields = ("stored_file", "related_module", "related_item_type", "relation_type", "is_primary")
    search_fields = ("related_module", "related_item_type", "related_item_id", "relation_type")
    ordering_fields = ("created_at", "updated_at")


class MediaAssetViewSet(FilesCenterBaseViewSet):
    queryset = MediaAsset.objects.select_related("stored_file").all()
    serializer_class = MediaAssetSerializer
    filterset_fields = ("stored_file", "asset_type", "is_active")
    search_fields = ("title", "alt_text", "caption", "stored_file__original_name")
    ordering_fields = ("ordering", "created_at", "updated_at")


class FileVersionViewSet(FilesCenterBaseViewSet):
    queryset = FileVersion.objects.select_related("parent_file", "stored_file", "created_by").all()
    serializer_class = FileVersionSerializer
    filterset_fields = ("parent_file", "stored_file", "created_by")
    search_fields = ("version_label", "notes", "parent_file__original_name", "stored_file__original_name")
    ordering_fields = ("created_at", "updated_at")


class FileAccessLogViewSet(FilesCenterBaseViewSet):
    queryset = FileAccessLog.objects.select_related("stored_file", "accessed_by").all()
    serializer_class = FileAccessLogSerializer
    filterset_fields = ("stored_file", "accessed_by", "action_type")
    search_fields = ("stored_file__original_name", "ip_address", "user_agent")
    ordering_fields = ("accessed_at", "created_at")


class FileCollectionViewSet(FilesCenterBaseViewSet):
    queryset = FileCollection.objects.select_related("created_by").all()
    serializer_class = FileCollectionSerializer
    filterset_fields = ("collection_type", "created_by", "is_active")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "created_at", "updated_at")


class FileCollectionItemViewSet(FilesCenterBaseViewSet):
    queryset = FileCollectionItem.objects.select_related("collection", "stored_file").all()
    serializer_class = FileCollectionItemSerializer
    filterset_fields = ("collection", "stored_file", "is_primary")
    search_fields = ("collection__name", "stored_file__original_name")
    ordering_fields = ("ordering", "created_at", "updated_at")

