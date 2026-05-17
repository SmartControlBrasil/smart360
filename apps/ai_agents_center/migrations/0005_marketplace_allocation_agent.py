import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("marketplace_technicians", "0003_matching_score_breakdown"),
        ("ai_agents_center", "0004_profitability_agent"),
    ]

    operations = [
        migrations.CreateModel(
            name="AgentMarketplaceRequestFlag",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("best_candidate_profile_id", models.PositiveBigIntegerField(blank=True, db_index=True, null=True)),
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
                        related_name="marketplace_request_flags",
                        to="ai_agents_center.agentdefinition",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="agent_marketplace_request_flags",
                        to="companies.company",
                    ),
                ),
                (
                    "latest_recommendation",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="marketplace_request_flags",
                        to="ai_agents_center.agentrecommendation",
                    ),
                ),
                (
                    "latest_run",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="marketplace_request_flags",
                        to="ai_agents_center.agentrun",
                    ),
                ),
                (
                    "service_request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="agent_marketplace_request_flags",
                        to="marketplace_technicians.technicianservicerequest",
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="agent_marketplace_request_flags",
                        to="smart_system.operationalsite",
                    ),
                ),
            ],
            options={
                "db_table": "ai_agents_marketplace_request_flags",
                "ordering": ["-attention_score", "-updated_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="agentmarketplacerequestflag",
            constraint=models.UniqueConstraint(
                fields=("agent", "company", "service_request"),
                name="uniq_ai_agents_marketplace_request_flag",
            ),
        ),
    ]
