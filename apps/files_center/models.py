import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def stored_file_upload_to(instance, filename):
    return f"files_center/{timezone.now():%Y/%m/%d}/{instance.stored_name or filename}"


class FileCategory(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    ordering = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "files_center_categories"
        ordering = ["ordering", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class StoredFile(models.Model):
    class StorageBackend(models.TextChoices):
        LOCAL = "local", "Local"
        S3 = "s3", "S3"
        MINIO = "minio", "MinIO"
        CUSTOM = "custom", "Custom"

    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        INTERNAL = "internal", "Internal"
        PUBLIC = "public", "Public"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    original_name = models.CharField(max_length=255)
    stored_name = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to=stored_file_upload_to)
    mime_type = models.CharField(max_length=120)
    extension = models.CharField(max_length=20, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    category = models.ForeignKey(
        "files_center.FileCategory",
        on_delete=models.SET_NULL,
        related_name="files",
        null=True,
        blank=True,
    )
    storage_backend = models.CharField(max_length=20, choices=StorageBackend.choices, default=StorageBackend.LOCAL)
    checksum = models.CharField(max_length=128, blank=True)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PRIVATE)
    is_active = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="stored_files",
        null=True,
        blank=True,
    )
    uploaded_at = models.DateTimeField(default=timezone.now)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "files_center_stored_files"
        ordering = ["-uploaded_at", "-created_at"]

    def save(self, *args, **kwargs):
        if not self.stored_name:
            extension = os.path.splitext(self.original_name or "")[1]
            self.stored_name = f"{uuid.uuid4().hex}{extension}"
        if not self.extension and self.original_name:
            self.extension = os.path.splitext(self.original_name)[1].lstrip(".").lower()
        if self.file and not self.size_bytes:
            self.size_bytes = getattr(self.file, "size", 0) or 0
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.original_name


class FileLink(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    stored_file = models.ForeignKey("files_center.StoredFile", on_delete=models.CASCADE, related_name="links")
    related_module = models.CharField(max_length=80, db_index=True)
    related_item_type = models.CharField(max_length=80)
    related_item_id = models.CharField(max_length=120)
    relation_type = models.CharField(max_length=80)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "files_center_file_links"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.related_module}:{self.related_item_type}:{self.related_item_id}"


class MediaAsset(models.Model):
    class AssetType(models.TextChoices):
        HERO_IMAGE = "hero_image", "Hero Image"
        GALLERY_IMAGE = "gallery_image", "Gallery Image"
        PRODUCT_IMAGE = "product_image", "Product Image"
        PROFILE_IMAGE = "profile_image", "Profile Image"
        DOCUMENT_PREVIEW = "document_preview", "Document Preview"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    stored_file = models.ForeignKey("files_center.StoredFile", on_delete=models.CASCADE, related_name="media_assets")
    asset_type = models.CharField(max_length=30, choices=AssetType.choices, default=AssetType.GALLERY_IMAGE)
    title = models.CharField(max_length=180, blank=True)
    alt_text = models.CharField(max_length=255, blank=True)
    caption = models.TextField(blank=True)
    ordering = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "files_center_media_assets"
        ordering = ["ordering", "id"]

    def __str__(self) -> str:
        return self.title or self.stored_file.original_name


class FileVersion(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    parent_file = models.ForeignKey("files_center.StoredFile", on_delete=models.CASCADE, related_name="versions")
    stored_file = models.ForeignKey("files_center.StoredFile", on_delete=models.CASCADE, related_name="version_entries")
    version_label = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="file_versions_created",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "files_center_file_versions"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["parent_file", "version_label"], name="uniq_file_version_label"),
        ]

    def __str__(self) -> str:
        return f"{self.parent_file} - {self.version_label}"


class FileAccessLog(models.Model):
    class ActionType(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        VIEWED = "viewed", "Viewed"
        DOWNLOADED = "downloaded", "Downloaded"
        DELETED = "deleted", "Deleted"
        LINKED = "linked", "Linked"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    stored_file = models.ForeignKey("files_center.StoredFile", on_delete=models.CASCADE, related_name="access_logs")
    accessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="file_access_logs",
        null=True,
        blank=True,
    )
    action_type = models.CharField(max_length=20, choices=ActionType.choices, default=ActionType.VIEWED)
    ip_address = models.CharField(max_length=64, blank=True)
    user_agent = models.TextField(blank=True)
    accessed_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "files_center_access_logs"
        ordering = ["-accessed_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.stored_file} - {self.action_type}"


class FileCollection(models.Model):
    class CollectionType(models.TextChoices):
        GALLERY = "gallery", "Gallery"
        DOCUMENT_PACKAGE = "document_package", "Document Package"
        BRANDING_KIT = "branding_kit", "Branding Kit"
        VERIFICATION_SET = "verification_set", "Verification Set"
        CUSTOM = "custom", "Custom"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    description = models.TextField(blank=True)
    collection_type = models.CharField(max_length=30, choices=CollectionType.choices, default=CollectionType.CUSTOM)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="file_collections_created",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "files_center_collections"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class FileCollectionItem(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    collection = models.ForeignKey("files_center.FileCollection", on_delete=models.CASCADE, related_name="items")
    stored_file = models.ForeignKey("files_center.StoredFile", on_delete=models.CASCADE, related_name="collection_items")
    ordering = models.PositiveIntegerField(default=1)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "files_center_collection_items"
        ordering = ["ordering", "id"]
        constraints = [
            models.UniqueConstraint(fields=["collection", "stored_file"], name="uniq_collection_stored_file"),
        ]

    def __str__(self) -> str:
        return f"{self.collection} - {self.stored_file}"

