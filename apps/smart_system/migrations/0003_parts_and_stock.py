import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0002_sitemembership"),
        ("smart_system", "0002_multitenant_scope"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Part",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("code", models.CharField(max_length=60)),
                ("name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("manufacturer", models.CharField(blank=True, max_length=120)),
                ("model", models.CharField(blank=True, max_length=120)),
                ("category", models.CharField(blank=True, max_length=120)),
                ("unit", models.CharField(default="un", max_length=30)),
                ("unit_cost", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("current_stock", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("minimum_stock", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("maximum_stock", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("location", models.CharField(blank=True, max_length=180)),
                ("primary_supplier", models.CharField(blank=True, max_length=180)),
                ("status", models.CharField(choices=[("active", "Active"), ("inactive", "Inactive"), ("discontinued", "Discontinued")], default="active", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="smart_system_parts", to="companies.company")),
                ("operational_site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="parts", to="smart_system.operationalsite")),
            ],
            options={
                "db_table": "smart_system_parts",
                "ordering": ["company__name", "code"],
            },
        ),
        migrations.AddConstraint(
            model_name="part",
            constraint=models.UniqueConstraint(fields=("company", "code"), name="uniq_smart_system_part_company_code"),
        ),
        migrations.CreateModel(
            name="PartAssetLink",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("quantity_recommended", models.DecimalField(decimal_places=2, default=1, max_digits=12)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="part_links", to="smart_system.asset")),
                ("part", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="asset_links", to="smart_system.part")),
            ],
            options={
                "db_table": "smart_system_part_asset_links",
                "ordering": ["asset__asset_tag", "part__code"],
            },
        ),
        migrations.AddConstraint(
            model_name="partassetlink",
            constraint=models.UniqueConstraint(fields=("part", "asset"), name="uniq_smart_system_part_asset_link"),
        ),
        migrations.CreateModel(
            name="StockMovement",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("movement_type", models.CharField(choices=[("inbound", "Inbound"), ("outbound", "Outbound"), ("adjustment", "Adjustment")], max_length=20)),
                ("quantity", models.DecimalField(decimal_places=2, max_digits=12)),
                ("reference_type", models.CharField(blank=True, max_length=80)),
                ("reference_id", models.CharField(blank=True, max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="smart_system_stock_movements", to="companies.company")),
                ("operational_site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="stock_movements", to="smart_system.operationalsite")),
                ("part", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="stock_movements", to="smart_system.part")),
                ("performed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="stock_movements", to=settings.AUTH_USER_MODEL)),
                ("service_order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="stock_movements", to="smart_system.serviceorder")),
            ],
            options={
                "db_table": "smart_system_stock_movements",
                "ordering": ["-occurred_at", "-created_at"],
            },
        ),
    ]
