from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0001_initial"),
        ("smart_system", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ai_agents_center", "0008_technician_copilot"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientPortalCopilotConfiguration",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("is_enabled", models.BooleanField(default=True)),
                ("default_suggestions", models.JSONField(blank=True, default=list)),
                ("behavior_config", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="client_portal_copilot_configurations",
                        to="companies.company",
                    ),
                ),
            ],
            options={
                "db_table": "ai_client_portal_copilot_configurations",
                "ordering": ["company__name", "created_at"],
            },
        ),
        migrations.CreateModel(
            name="ClientPortalCopilotSession",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("status", models.CharField(choices=[("active", "Active"), ("reset", "Reset"), ("closed", "Closed")], db_index=True, default="active", max_length=20)),
                ("title", models.CharField(blank=True, max_length=180)),
                ("current_context", models.JSONField(blank=True, default=dict)),
                ("last_intent", models.CharField(blank=True, db_index=True, max_length=60)),
                ("last_query", models.TextField(blank=True)),
                ("message_count", models.PositiveIntegerField(default=0)),
                ("last_activity_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="client_portal_copilot_sessions",
                        to="companies.company",
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="client_portal_copilot_sessions",
                        to="smart_system.operationalsite",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="client_portal_copilot_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "ai_client_portal_copilot_sessions",
                "ordering": ["-last_activity_at", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ClientPortalCopilotMessage",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("role", models.CharField(choices=[("user", "User"), ("assistant", "Assistant"), ("system", "System")], db_index=True, max_length=20)),
                ("content", models.TextField(blank=True)),
                ("detected_intent", models.CharField(blank=True, db_index=True, max_length=60)),
                ("context_snapshot", models.JSONField(blank=True, default=dict)),
                ("structured_payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="ai_agents_center.clientportalcopilotsession",
                    ),
                ),
            ],
            options={
                "db_table": "ai_client_portal_copilot_messages",
                "ordering": ["created_at", "id"],
            },
        ),
    ]
