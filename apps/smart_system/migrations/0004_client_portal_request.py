from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0002_sitemembership"),
        ("smart_system", "0003_parts_and_stock"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientPortalRequest",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("protocol_number", models.CharField(max_length=40, unique=True)),
                ("title", models.CharField(max_length=180)),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("maintenance", "Maintenance"),
                            ("inspection", "Inspection"),
                            ("report", "Report"),
                            ("access", "Access"),
                            ("other", "Other"),
                        ],
                        default="maintenance",
                        max_length=20,
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("low", "Low"),
                            ("medium", "Medium"),
                            ("high", "High"),
                            ("urgent", "Urgent"),
                        ],
                        default="medium",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("under_review", "Under Review"),
                            ("in_progress", "In Progress"),
                            ("resolved", "Resolved"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="open",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField()),
                ("contact_name", models.CharField(blank=True, max_length=120)),
                ("contact_email", models.EmailField(blank=True, max_length=254)),
                ("contact_phone", models.CharField(blank=True, max_length=30)),
                ("desired_date", models.DateField(blank=True, null=True)),
                ("last_customer_update_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("internal_notes", models.TextField(blank=True)),
                ("resolution_summary", models.TextField(blank=True)),
                ("marketplace_request_reference", models.CharField(blank=True, max_length=100)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "asset",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="client_portal_requests",
                        to="smart_system.asset",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="client_portal_requests",
                        to="companies.company",
                    ),
                ),
                (
                    "operational_site",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="client_portal_requests",
                        to="smart_system.operationalsite",
                    ),
                ),
                (
                    "related_service_order",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="client_portal_requests",
                        to="smart_system.serviceorder",
                    ),
                ),
                (
                    "requester",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="client_portal_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "smart_system_client_portal_requests",
                "ordering": ["-created_at"],
            },
        ),
    ]
