import django.db.models.deletion
import django.utils.timezone
import uuid

from django.conf import settings
from django.db import migrations, models

import apps.files_center.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FileCategory",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(blank=True, max_length=140, unique=True)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("ordering", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "files_center_categories", "ordering": ["ordering", "name"]},
        ),
        migrations.CreateModel(
            name="FileCollection",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("description", models.TextField(blank=True)),
                (
                    "collection_type",
                    models.CharField(
                        choices=[
                            ("gallery", "Gallery"),
                            ("document_package", "Document Package"),
                            ("branding_kit", "Branding Kit"),
                            ("verification_set", "Verification Set"),
                            ("custom", "Custom"),
                        ],
                        default="custom",
                        max_length=30,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="file_collections_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "files_center_collections", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="StoredFile",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("original_name", models.CharField(max_length=255)),
                ("stored_name", models.CharField(blank=True, max_length=255)),
                ("file", models.FileField(upload_to=apps.files_center.models.stored_file_upload_to)),
                ("mime_type", models.CharField(max_length=120)),
                ("extension", models.CharField(blank=True, max_length=20)),
                ("size_bytes", models.PositiveBigIntegerField(default=0)),
                (
                    "storage_backend",
                    models.CharField(
                        choices=[("local", "Local"), ("s3", "S3"), ("minio", "MinIO"), ("custom", "Custom")],
                        default="local",
                        max_length=20,
                    ),
                ),
                ("checksum", models.CharField(blank=True, max_length=128)),
                (
                    "visibility",
                    models.CharField(
                        choices=[("private", "Private"), ("internal", "Internal"), ("public", "Public")],
                        default="private",
                        max_length=20,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("uploaded_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "category",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="files",
                        to="files_center.filecategory",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="stored_files",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "files_center_stored_files", "ordering": ["-uploaded_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="FileAccessLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "action_type",
                    models.CharField(
                        choices=[
                            ("uploaded", "Uploaded"),
                            ("viewed", "Viewed"),
                            ("downloaded", "Downloaded"),
                            ("deleted", "Deleted"),
                            ("linked", "Linked"),
                        ],
                        default="viewed",
                        max_length=20,
                    ),
                ),
                ("ip_address", models.CharField(blank=True, max_length=64)),
                ("user_agent", models.TextField(blank=True)),
                ("accessed_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "accessed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="file_access_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "stored_file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_logs",
                        to="files_center.storedfile",
                    ),
                ),
            ],
            options={"db_table": "files_center_access_logs", "ordering": ["-accessed_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="FileCollectionItem",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("ordering", models.PositiveIntegerField(default=1)),
                ("is_primary", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "collection",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="files_center.filecollection",
                    ),
                ),
                (
                    "stored_file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="collection_items",
                        to="files_center.storedfile",
                    ),
                ),
            ],
            options={"db_table": "files_center_collection_items", "ordering": ["ordering", "id"]},
        ),
        migrations.CreateModel(
            name="FileLink",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("related_module", models.CharField(db_index=True, max_length=80)),
                ("related_item_type", models.CharField(max_length=80)),
                ("related_item_id", models.CharField(max_length=120)),
                ("relation_type", models.CharField(max_length=80)),
                ("is_primary", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "stored_file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="links",
                        to="files_center.storedfile",
                    ),
                ),
            ],
            options={"db_table": "files_center_file_links", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="MediaAsset",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "asset_type",
                    models.CharField(
                        choices=[
                            ("hero_image", "Hero Image"),
                            ("gallery_image", "Gallery Image"),
                            ("product_image", "Product Image"),
                            ("profile_image", "Profile Image"),
                            ("document_preview", "Document Preview"),
                        ],
                        default="gallery_image",
                        max_length=30,
                    ),
                ),
                ("title", models.CharField(blank=True, max_length=180)),
                ("alt_text", models.CharField(blank=True, max_length=255)),
                ("caption", models.TextField(blank=True)),
                ("ordering", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "stored_file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="media_assets",
                        to="files_center.storedfile",
                    ),
                ),
            ],
            options={"db_table": "files_center_media_assets", "ordering": ["ordering", "id"]},
        ),
        migrations.CreateModel(
            name="FileVersion",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("version_label", models.CharField(max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("notes", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="file_versions_created",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "parent_file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="versions",
                        to="files_center.storedfile",
                    ),
                ),
                (
                    "stored_file",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="version_entries",
                        to="files_center.storedfile",
                    ),
                ),
            ],
            options={"db_table": "files_center_file_versions", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="filecollectionitem",
            constraint=models.UniqueConstraint(fields=("collection", "stored_file"), name="uniq_collection_stored_file"),
        ),
        migrations.AddConstraint(
            model_name="fileversion",
            constraint=models.UniqueConstraint(fields=("parent_file", "version_label"), name="uniq_file_version_label"),
        ),
    ]

