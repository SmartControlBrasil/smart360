import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AutomationTask",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("task_name", models.CharField(max_length=160)),
                (
                    "task_type",
                    models.CharField(
                        choices=[
                            ("workflow", "Workflow"),
                            ("notification", "Notification"),
                            ("snapshot", "Snapshot"),
                            ("metric", "Metric"),
                            ("sync", "Sync"),
                            ("custom", "Custom"),
                        ],
                        default="custom",
                        max_length=20,
                    ),
                ),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                ("target_module", models.CharField(blank=True, max_length=80)),
                ("payload", models.JSONField(blank=True, default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("scheduled", "Scheduled"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("scheduled_at", models.DateTimeField(blank=True, null=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("retry_count", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("correlation_id", models.CharField(blank=True, db_index=True, max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "integration_automation_tasks", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="DeadLetterEvent",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("original_event_name", models.CharField(db_index=True, max_length=120)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("failure_reason", models.TextField()),
                ("retry_count", models.PositiveIntegerField(default=0)),
                ("moved_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "integration_dead_letter_events", "ordering": ["-moved_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="EventSubscription",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("event_name", models.CharField(db_index=True, max_length=120)),
                ("target_module", models.CharField(db_index=True, max_length=80)),
                ("handler_name", models.CharField(max_length=160)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "execution_mode",
                    models.CharField(
                        choices=[("sync", "Sync"), ("async", "Async"), ("manual", "Manual")],
                        default="async",
                        max_length=10,
                    ),
                ),
                ("retry_policy", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "integration_event_subscriptions", "ordering": ["event_name", "target_module", "handler_name"]},
        ),
        migrations.CreateModel(
            name="IntegrationEvent",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("event_name", models.CharField(db_index=True, max_length=120)),
                ("event_key", models.SlugField(blank=True, max_length=180, unique=True)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                (
                    "event_type",
                    models.CharField(
                        choices=[("domain", "Domain"), ("integration", "Integration"), ("system", "System")],
                        default="integration",
                        max_length=20,
                    ),
                ),
                ("aggregate_type", models.CharField(blank=True, max_length=80)),
                ("aggregate_id", models.CharField(blank=True, max_length=120)),
                ("payload", models.JSONField(blank=True, default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("published", "Published"),
                            ("processing", "Processing"),
                            ("processed", "Processed"),
                            ("failed", "Failed"),
                            ("dead_letter", "Dead Letter"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("occurred_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("retry_count", models.PositiveIntegerField(default=0)),
                ("error_message", models.TextField(blank=True)),
                ("correlation_id", models.CharField(blank=True, db_index=True, max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "integration_events", "ordering": ["-occurred_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="IntegrationLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                ("target_module", models.CharField(blank=True, max_length=80)),
                ("event_name", models.CharField(blank=True, max_length=120)),
                ("task_name", models.CharField(blank=True, max_length=160)),
                (
                    "log_level",
                    models.CharField(
                        choices=[
                            ("debug", "Debug"),
                            ("info", "Info"),
                            ("warning", "Warning"),
                            ("error", "Error"),
                            ("critical", "Critical"),
                        ],
                        default="info",
                        max_length=20,
                    ),
                ),
                ("message", models.TextField()),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "integration_logs", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="WorkflowDefinition",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("description", models.TextField(blank=True)),
                ("trigger_event_name", models.CharField(db_index=True, max_length=120)),
                (
                    "workflow_type",
                    models.CharField(
                        choices=[
                            ("event_driven", "Event Driven"),
                            ("orchestration", "Orchestration"),
                            ("automation", "Automation"),
                        ],
                        default="event_driven",
                        max_length=20,
                    ),
                ),
                ("config_json", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "integration_workflow_definitions", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="WorkflowExecution",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("output_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "integration_event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="workflow_executions",
                        to="integration_bus.integrationevent",
                    ),
                ),
                (
                    "workflow_definition",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="executions",
                        to="integration_bus.workflowdefinition",
                    ),
                ),
            ],
            options={"db_table": "integration_workflow_executions", "ordering": ["-started_at", "-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="eventsubscription",
            constraint=models.UniqueConstraint(
                fields=("event_name", "target_module", "handler_name"),
                name="uniq_integration_subscription_handler",
            ),
        ),
    ]

