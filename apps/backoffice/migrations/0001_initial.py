import django.db.models.deletion
import django.utils.timezone
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="BackofficeAlert",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("title", models.CharField(max_length=180)),
                ("slug", models.SlugField(blank=True, max_length=200, unique=True)),
                (
                    "alert_type",
                    models.CharField(
                        choices=[
                            ("operational", "Operational"),
                            ("security", "Security"),
                            ("billing", "Billing"),
                            ("workflow", "Workflow"),
                            ("review", "Review"),
                        ],
                        default="operational",
                        max_length=20,
                    ),
                ),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                (
                    "severity",
                    models.CharField(
                        choices=[("info", "Info"), ("warning", "Warning"), ("critical", "Critical")],
                        default="warning",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("acknowledged", "Acknowledged"),
                            ("resolved", "Resolved"),
                            ("dismissed", "Dismissed"),
                        ],
                        default="open",
                        max_length=20,
                    ),
                ),
                ("related_item_type", models.CharField(blank=True, max_length=80)),
                ("related_item_id", models.CharField(blank=True, max_length=120)),
                ("summary", models.CharField(max_length=255)),
                ("details", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "backoffice_alerts", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="BackofficeQueue",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                (
                    "queue_type",
                    models.CharField(
                        choices=[
                            ("review", "Review"),
                            ("operational", "Operational"),
                            ("approval", "Approval"),
                            ("billing", "Billing"),
                            ("incident", "Incident"),
                        ],
                        default="operational",
                        max_length=20,
                    ),
                ),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("ordering", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "backoffice_queues", "ordering": ["ordering", "name"]},
        ),
        migrations.CreateModel(
            name="BackofficeQuickAction",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("target_module", models.CharField(db_index=True, max_length=80)),
                (
                    "action_type",
                    models.CharField(
                        choices=[
                            ("navigation", "Navigation"),
                            ("review", "Review"),
                            ("create", "Create"),
                            ("approve", "Approve"),
                            ("reject", "Reject"),
                        ],
                        default="navigation",
                        max_length=20,
                    ),
                ),
                ("label", models.CharField(max_length=120)),
                ("route_path", models.CharField(blank=True, max_length=255)),
                ("config_json", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("ordering", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "backoffice_quick_actions", "ordering": ["ordering", "label"]},
        ),
        migrations.CreateModel(
            name="BackofficeWidget",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                (
                    "widget_type",
                    models.CharField(
                        choices=[
                            ("metric_card", "Metric Card"),
                            ("list", "List"),
                            ("alert_feed", "Alert Feed"),
                            ("task_feed", "Task Feed"),
                            ("queue_summary", "Queue Summary"),
                        ],
                        default="metric_card",
                        max_length=20,
                    ),
                ),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                ("title", models.CharField(max_length=180)),
                ("config_json", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("ordering", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "backoffice_widgets", "ordering": ["ordering", "title"]},
        ),
        migrations.CreateModel(
            name="BackofficeTask",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("title", models.CharField(max_length=180)),
                (
                    "task_type",
                    models.CharField(
                        choices=[
                            ("review", "Review"),
                            ("approval", "Approval"),
                            ("follow_up", "Follow Up"),
                            ("escalation", "Escalation"),
                            ("internal", "Internal"),
                        ],
                        default="internal",
                        max_length=20,
                    ),
                ),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("in_progress", "In Progress"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                            ("blocked", "Blocked"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("urgent", "Urgent")],
                        default="medium",
                        max_length=20,
                    ),
                ),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("related_item_type", models.CharField(blank=True, max_length=80)),
                ("related_item_id", models.CharField(blank=True, max_length=120)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_to",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="backoffice_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "backoffice_tasks", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="BackofficeNote",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "note_type",
                    models.CharField(
                        choices=[
                            ("review", "Review"),
                            ("internal", "Internal"),
                            ("approval", "Approval"),
                            ("incident", "Incident"),
                        ],
                        default="internal",
                        max_length=20,
                    ),
                ),
                ("related_item_type", models.CharField(max_length=80)),
                ("related_item_id", models.CharField(max_length=120)),
                ("content", models.TextField()),
                ("is_private", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="backoffice_notes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "backoffice_notes", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="BackofficeQueueItem",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("item_type", models.CharField(max_length=80)),
                ("item_id", models.CharField(max_length=120)),
                ("reference_label", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("in_progress", "In Progress"),
                            ("reviewed", "Reviewed"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("resolved", "Resolved"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("urgent", "Urgent")],
                        default="medium",
                        max_length=20,
                    ),
                ),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_to",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="backoffice_queue_items",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "queue",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="backoffice.backofficequeue",
                    ),
                ),
            ],
            options={"db_table": "backoffice_queue_items", "ordering": ["queue__ordering", "-created_at"]},
        ),
    ]

