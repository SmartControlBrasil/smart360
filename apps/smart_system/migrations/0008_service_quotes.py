from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("smart_system", "0007_schedule_routing"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="serviceorder",
            name="quote_approved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="serviceorder",
            name="quote_required",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="serviceorder",
            name="quote_status",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.CreateModel(
            name="ServiceQuote",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("quote_number", models.CharField(max_length=40, unique=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("sent", "Sent"), ("approved", "Approved"), ("rejected", "Rejected"), ("expired", "Expired")], default="draft", max_length=20)),
                ("total_parts", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("total_labor", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("total_value", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("notes", models.TextField(blank=True)),
                ("customer_message", models.TextField(blank=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("rejected_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("approved_by_name", models.CharField(blank=True, max_length=180)),
                ("approval_notes", models.TextField(blank=True)),
                ("rejection_reason", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("approved_by_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="approved_service_quotes", to=settings.AUTH_USER_MODEL)),
                ("asset", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="service_quotes", to="smart_system.asset")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="service_quotes", to="companies.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_service_quotes", to=settings.AUTH_USER_MODEL)),
                ("operational_site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="service_quotes", to="smart_system.operationalsite")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_service_quotes", to=settings.AUTH_USER_MODEL)),
                ("work_order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quotes", to="smart_system.serviceorder")),
            ],
            options={
                "db_table": "smart_system_service_quotes",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="QuoteItem",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("item_type", models.CharField(choices=[("part", "Part"), ("labor", "Labor"), ("service", "Service")], max_length=20)),
                ("description", models.CharField(max_length=255)),
                ("part_reference", models.CharField(blank=True, max_length=120)),
                ("available_quantity", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("quantity", models.DecimalField(decimal_places=2, default=1, max_digits=12)),
                ("unit_price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("total_price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("estimated_minutes", models.PositiveIntegerField(default=0)),
                ("hourly_rate", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("notes", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("quote", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="smart_system.servicequote")),
                ("stock_item", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="quote_items", to="smart_system.part")),
            ],
            options={
                "db_table": "smart_system_quote_items",
                "ordering": ["id"],
            },
        ),
        migrations.AddIndex(
            model_name="servicequote",
            index=models.Index(fields=["company", "status"], name="smart_quote_company_status_idx"),
        ),
        migrations.AddIndex(
            model_name="servicequote",
            index=models.Index(fields=["work_order", "status"], name="smart_quote_order_status_idx"),
        ),
    ]
