from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0001_initial"),
        ("smart_system", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ai_agents_center", "0009_client_portal_copilot"),
    ]

    operations = [
        migrations.CreateModel(
            name="AIBriefingConfiguration",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("is_enabled", models.BooleanField(default=True)),
                ("delivery_channels", models.JSONField(blank=True, default=list)),
                ("default_schedule", models.JSONField(blank=True, default=dict)),
                ("behavior_config", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_briefing_configurations",
                        to="companies.company",
                    ),
                ),
            ],
            options={
                "db_table": "ai_briefing_configurations",
                "ordering": ["company__name", "created_at"],
            },
        ),
        migrations.CreateModel(
            name="AIBriefing",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("briefing_type", models.CharField(choices=[("daily_executive", "Daily Executive Briefing"), ("daily_field", "Daily Field Briefing"), ("daily_client", "Daily Client Briefing"), ("weekly_executive", "Weekly Executive Summary"), ("on_demand", "On-demand Briefing")], db_index=True, max_length=40)),
                ("audience", models.CharField(choices=[("manager", "Manager"), ("technician", "Technician"), ("client", "Client")], db_index=True, max_length=20)),
                ("title", models.CharField(max_length=200)),
                ("summary", models.TextField(blank=True)),
                ("period_label", models.CharField(blank=True, max_length=120)),
                ("period_start", models.DateField(blank=True, null=True)),
                ("period_end", models.DateField(blank=True, null=True)),
                ("content", models.JSONField(blank=True, default=dict)),
                ("source_agents", models.JSONField(blank=True, default=list)),
                ("source_recommendation_ids", models.JSONField(blank=True, default=list)),
                ("source_proposal_ids", models.JSONField(blank=True, default=list)),
                ("filters", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("generated", "Generated"), ("delivered", "Delivered"), ("viewed", "Viewed"), ("failed", "Failed"), ("cancelled", "Cancelled")], db_index=True, default="generated", max_length=20)),
                ("generated_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("viewed_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_briefings",
                        to="companies.company",
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ai_briefings",
                        to="smart_system.operationalsite",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ai_briefings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "ai_briefings",
                "ordering": ["-generated_at", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AIBriefingDelivery",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("channel", models.CharField(choices=[("dashboard", "Dashboard"), ("portal", "Portal"), ("field_app", "Field App"), ("in_app", "In App"), ("email", "Email"), ("push", "Push")], db_index=True, max_length=20)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("delivered", "Delivered"), ("viewed", "Viewed"), ("failed", "Failed")], db_index=True, default="pending", max_length=20)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("viewed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "briefing",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deliveries",
                        to="ai_agents_center.aibriefing",
                    ),
                ),
                (
                    "recipient_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ai_briefing_deliveries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "ai_briefing_deliveries",
                "ordering": ["-created_at"],
            },
        ),
    ]
