import django.db.models.deletion
import django.utils.timezone
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExportProfile",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("slug", models.SlugField(blank=True, max_length=200, unique=True)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                (
                    "export_type",
                    models.CharField(
                        choices=[
                            ("operational", "Operational"),
                            ("list", "List"),
                            ("analytical", "Analytical"),
                            ("custom", "Custom"),
                        ],
                        default="operational",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("columns_config", models.JSONField(blank=True, default=list)),
                ("filters_config", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="export_profiles",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "reporting_center_export_profiles", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="ReportTemplate",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("slug", models.SlugField(blank=True, max_length=200, unique=True)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                (
                    "report_type",
                    models.CharField(
                        choices=[
                            ("operational", "Operational"),
                            ("managerial", "Managerial"),
                            ("financial", "Financial"),
                            ("analytical", "Analytical"),
                            ("custom", "Custom"),
                        ],
                        default="operational",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                (
                    "output_format_default",
                    models.CharField(
                        choices=[
                            ("csv", "CSV"),
                            ("xlsx", "XLSX"),
                            ("json", "JSON"),
                            ("pdf_future", "PDF Future"),
                        ],
                        default="json",
                        max_length=20,
                    ),
                ),
                ("config_json", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "reporting_center_templates", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="ExportExecution",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "output_format",
                    models.CharField(
                        choices=[("csv", "CSV"), ("xlsx", "XLSX"), ("json", "JSON")],
                        default="json",
                        max_length=20,
                    ),
                ),
                ("filters_json", models.JSONField(blank=True, default=dict)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "export_profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="executions",
                        to="reporting_center.exportprofile",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="export_executions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "reporting_center_export_executions", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ReportRequest",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "output_format",
                    models.CharField(
                        choices=[
                            ("csv", "CSV"),
                            ("xlsx", "XLSX"),
                            ("json", "JSON"),
                            ("pdf_future", "PDF Future"),
                        ],
                        default="json",
                        max_length=20,
                    ),
                ),
                ("filters_json", models.JSONField(blank=True, default=dict)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="report_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "requested_for_company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="report_requests",
                        to="companies.company",
                    ),
                ),
                (
                    "template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="requests",
                        to="reporting_center.reporttemplate",
                    ),
                ),
            ],
            options={"db_table": "reporting_center_report_requests", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ScheduledReport",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("slug", models.SlugField(blank=True, max_length=200, unique=True)),
                (
                    "schedule_type",
                    models.CharField(
                        choices=[
                            ("daily", "Daily"),
                            ("weekly", "Weekly"),
                            ("monthly", "Monthly"),
                            ("custom", "Custom"),
                        ],
                        default="weekly",
                        max_length=20,
                    ),
                ),
                ("schedule_config", models.JSONField(blank=True, default=dict)),
                (
                    "output_format",
                    models.CharField(
                        choices=[
                            ("csv", "CSV"),
                            ("xlsx", "XLSX"),
                            ("json", "JSON"),
                            ("pdf_future", "PDF Future"),
                        ],
                        default="json",
                        max_length=20,
                    ),
                ),
                ("filters_json", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("last_run_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner_company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scheduled_reports",
                        to="companies.company",
                    ),
                ),
                (
                    "owner_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scheduled_reports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scheduled_reports",
                        to="reporting_center.reporttemplate",
                    ),
                ),
            ],
            options={"db_table": "reporting_center_scheduled_reports", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="ReportArtifact",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("file", models.FileField(blank=True, upload_to="reporting_center/artifacts/")),
                (
                    "artifact_type",
                    models.CharField(
                        choices=[
                            ("csv", "CSV"),
                            ("xlsx", "XLSX"),
                            ("json", "JSON"),
                            ("pdf_future", "PDF Future"),
                        ],
                        default="json",
                        max_length=20,
                    ),
                ),
                ("storage_path", models.CharField(blank=True, max_length=255)),
                ("file_name", models.CharField(blank=True, max_length=255)),
                ("mime_type", models.CharField(blank=True, max_length=120)),
                ("size_bytes", models.PositiveBigIntegerField(default=0)),
                ("generated_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "report_request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="artifacts",
                        to="reporting_center.reportrequest",
                    ),
                ),
            ],
            options={"db_table": "reporting_center_report_artifacts", "ordering": ["-generated_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="ReportLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                (
                    "log_level",
                    models.CharField(
                        choices=[("debug", "Debug"), ("info", "Info"), ("warning", "Warning"), ("error", "Error")],
                        default="info",
                        max_length=20,
                    ),
                ),
                ("message", models.TextField()),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "export_execution",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="logs",
                        to="reporting_center.exportexecution",
                    ),
                ),
                (
                    "report_request",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="logs",
                        to="reporting_center.reportrequest",
                    ),
                ),
            ],
            options={"db_table": "reporting_center_logs", "ordering": ["-created_at"]},
        ),
    ]

