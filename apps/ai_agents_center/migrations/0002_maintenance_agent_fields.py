from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ai_agents_center", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="agentactionproposal",
            name="priority",
            field=models.CharField(db_index=True, default="medium", max_length=20),
        ),
        migrations.AddField(
            model_name="agentactionproposal",
            name="summary",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="agentactionproposal",
            name="title",
            field=models.CharField(blank=True, max_length=240),
        ),
        migrations.AddField(
            model_name="agentrecommendation",
            name="attention_score",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="agentrecommendation",
            name="evidence_summary",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="agentrecommendation",
            name="explanation",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="agentrecommendation",
            name="priority",
            field=models.CharField(
                choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("immediate", "Immediate")],
                db_index=True,
                default="medium",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="agentrecommendation",
            name="requires_human_approval",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="agentrecommendation",
            name="suggested_action",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="agentrecommendation",
            name="recommendation_type",
            field=models.CharField(
                choices=[
                    ("insight", "Insight"),
                    ("preventive", "Preventive"),
                    ("rebalancing", "Rebalancing"),
                    ("profitability", "Profitability"),
                    ("marketplace", "Marketplace"),
                    ("anomaly", "Anomaly"),
                    ("preventive_review", "Preventive Review"),
                    ("extraordinary_inspection", "Extraordinary Inspection"),
                    ("failure_pattern_alert", "Failure Pattern Alert"),
                    ("reliability_attention", "Reliability Attention"),
                    ("action_plan_recommendation", "Action Plan Recommendation"),
                    ("critical_asset_watch", "Critical Asset Watch"),
                ],
                db_index=True,
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="AgentAssetAttentionFlag",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("status", models.CharField(choices=[("active", "Active"), ("watching", "Watching"), ("resolved", "Resolved")], db_index=True, default="active", max_length=20)),
                ("attention_score", models.PositiveSmallIntegerField(db_index=True, default=0)),
                ("summary", models.CharField(max_length=240)),
                ("risk_level", models.CharField(db_index=True, default="medium", max_length=20)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("last_detected_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("agent", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="asset_attention_flags", to="ai_agents_center.agentdefinition")),
                ("asset", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="agent_attention_flags", to="smart_system.asset")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="agent_asset_attention_flags", to="companies.company")),
                ("latest_recommendation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="asset_attention_flags", to="ai_agents_center.agentrecommendation")),
                ("latest_run", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="asset_attention_flags", to="ai_agents_center.agentrun")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="agent_asset_attention_flags", to="smart_system.operationalsite")),
            ],
            options={
                "db_table": "ai_agents_asset_attention_flags",
                "ordering": ["-attention_score", "-updated_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="agentassetattentionflag",
            constraint=models.UniqueConstraint(fields=("agent", "company", "asset"), name="uniq_ai_agents_asset_attention_flag"),
        ),
    ]
