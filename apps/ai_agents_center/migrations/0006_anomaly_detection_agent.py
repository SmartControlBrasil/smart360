from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("smart_system", "0009_maintenance_contracts"),
        ("ai_agents_center", "0005_marketplace_allocation_agent"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AgentAnomalyAttentionFlag",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "focus_type",
                    models.CharField(
                        choices=[
                            ("asset", "Asset"),
                            ("site", "Site"),
                            ("technician", "Technician"),
                            ("client", "Client"),
                            ("contract", "Contract"),
                            ("part", "Part"),
                            ("marketplace", "Marketplace"),
                            ("company", "Company"),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                ("target_entity_type", models.CharField(db_index=True, max_length=80)),
                ("target_entity_id", models.CharField(db_index=True, max_length=120)),
                ("display_label", models.CharField(max_length=240)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("watching", "Watching"), ("resolved", "Resolved")],
                        db_index=True,
                        default="active",
                        max_length=20,
                    ),
                ),
                ("attention_score", models.PositiveSmallIntegerField(db_index=True, default=0)),
                ("summary", models.CharField(max_length=240)),
                ("risk_level", models.CharField(db_index=True, default="medium", max_length=20)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("last_detected_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "agent",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="anomaly_attention_flags",
                        to="ai_agents_center.agentdefinition",
                    ),
                ),
                (
                    "asset",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="agent_anomaly_attention_flags",
                        to="smart_system.asset",
                    ),
                ),
                (
                    "client",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="agent_anomaly_attention_flags",
                        to="smart_system.maintenanceclient",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="agent_anomaly_attention_flags",
                        to="companies.company",
                    ),
                ),
                (
                    "contract",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="agent_anomaly_attention_flags",
                        to="smart_system.maintenancecontract",
                    ),
                ),
                (
                    "latest_recommendation",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="anomaly_attention_flags",
                        to="ai_agents_center.agentrecommendation",
                    ),
                ),
                (
                    "latest_run",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="anomaly_attention_flags",
                        to="ai_agents_center.agentrun",
                    ),
                ),
                (
                    "part",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="agent_anomaly_attention_flags",
                        to="smart_system.part",
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="agent_anomaly_attention_flags",
                        to="smart_system.operationalsite",
                    ),
                ),
                (
                    "technician",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="agent_anomaly_attention_flags",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "ai_agents_anomaly_attention_flags",
                "ordering": ["-attention_score", "-updated_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="agentanomalyattentionflag",
            constraint=models.UniqueConstraint(
                fields=("agent", "company", "focus_type", "target_entity_type", "target_entity_id"),
                name="uniq_ai_agents_anomaly_attention_flag",
            ),
        ),
    ]
