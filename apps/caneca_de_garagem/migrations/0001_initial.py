import django.db.models.deletion
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("market_core", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CreativeStoreProfile",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("display_name", models.CharField(max_length=180)),
                ("bio", models.TextField(blank=True)),
                ("profile_type", models.CharField(choices=[("sublimation", "Sublimation"), ("apparel", "Apparel"), ("handcraft", "Handcraft"), ("mixed", "Mixed")], default="mixed", max_length=20)),
                ("production_capabilities", models.JSONField(blank=True, default=list)),
                ("is_internal_factory", models.BooleanField(default=False)),
                ("lead_time_days", models.PositiveIntegerField(default=3)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("vendor", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="creative_profile", to="market_core.marketplacevendor")),
            ],
            options={"db_table": "cdg_creative_store_profiles", "ordering": ["display_name"]},
        ),
        migrations.CreateModel(
            name="CustomizationTemplate",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("template_name", models.CharField(max_length=150)),
                ("instructions", models.TextField(blank=True)),
                ("allowed_text_fields", models.JSONField(blank=True, default=list)),
                ("allowed_image_upload", models.BooleanField(default=True)),
                ("max_images", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="customization_templates", to="market_core.marketplaceproduct")),
            ],
            options={"db_table": "cdg_customization_templates", "ordering": ["template_name"]},
        ),
        migrations.CreateModel(
            name="CustomizationRequest",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("customer_text", models.JSONField(blank=True, default=dict)),
                ("uploaded_assets", models.JSONField(blank=True, default=list)),
                ("font_choice", models.CharField(blank=True, max_length=120)),
                ("color_choice", models.CharField(blank=True, max_length=120)),
                ("extra_notes", models.TextField(blank=True)),
                ("approval_status", models.CharField(choices=[("pending", "Pending"), ("approved", "Approved"), ("changes_requested", "Changes Requested")], default="pending", max_length=30)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("customization_template", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="requests", to="caneca_de_garagem.customizationtemplate")),
                ("order_item", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="customization_request", to="market_core.marketplaceorderitem")),
            ],
            options={"db_table": "cdg_customization_requests", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ArtworkAsset",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("file", models.FileField(upload_to="caneca_de_garagem/assets/")),
                ("asset_type", models.CharField(choices=[("image", "Image"), ("vector", "Vector"), ("pdf", "PDF"), ("other", "Other")], default="image", max_length=20)),
                ("original_name", models.CharField(max_length=255)),
                ("status", models.CharField(choices=[("uploaded", "Uploaded"), ("validated", "Validated"), ("rejected", "Rejected")], default="uploaded", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("customization_request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="artwork_assets", to="caneca_de_garagem.customizationrequest")),
            ],
            options={"db_table": "cdg_artwork_assets", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ProductionJob",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("job_type", models.CharField(choices=[("art_prep", "Art Preparation"), ("print", "Print"), ("sublimation", "Sublimation"), ("packaging", "Packaging")], max_length=20)),
                ("status", models.CharField(choices=[("queued", "Queued"), ("in_progress", "In Progress"), ("blocked", "Blocked"), ("completed", "Completed")], default="queued", max_length=20)),
                ("queue_position", models.PositiveIntegerField(blank=True, null=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="caneca_production_jobs", to=settings.AUTH_USER_MODEL)),
                ("internal_factory", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="factory_jobs", to="caneca_de_garagem.creativestoreprofile")),
                ("order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="production_jobs", to="market_core.marketplaceorder")),
                ("order_item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="production_jobs", to="market_core.marketplaceorderitem")),
                ("vendor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="production_jobs", to="market_core.marketplacevendor")),
            ],
            options={"db_table": "cdg_production_jobs", "ordering": ["queue_position", "-created_at"]},
        ),
        migrations.CreateModel(
            name="ProductionStep",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("step_name", models.CharField(max_length=150)),
                ("ordering", models.PositiveIntegerField(default=1)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("in_progress", "In Progress"), ("done", "Done"), ("blocked", "Blocked")], default="pending", max_length=20)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("production_job", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="steps", to="caneca_de_garagem.productionjob")),
            ],
            options={"db_table": "cdg_production_steps", "ordering": ["ordering", "id"]},
        ),
        migrations.CreateModel(
            name="ShipmentPreparation",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("shipping_status", models.CharField(choices=[("pending", "Pending"), ("ready", "Ready"), ("posted", "Posted"), ("delivered", "Delivered")], default="pending", max_length=20)),
                ("carrier", models.CharField(blank=True, max_length=120)),
                ("tracking_code", models.CharField(blank=True, max_length=120)),
                ("posted_at", models.DateTimeField(blank=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("order", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="shipment_preparation", to="market_core.marketplaceorder")),
            ],
            options={"db_table": "cdg_shipment_preparations", "ordering": ["-created_at"]},
        ),
    ]
