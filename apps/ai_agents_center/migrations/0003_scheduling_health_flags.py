from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("ai_agents_center", "0002_maintenance_agent_fields"),
    ]

    operations = [
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
                    ("technician_overload", "Technician Overload"),
                    ("route_reorder", "Route Reorder"),
                    ("visit_reassignment", "Visit Reassignment"),
                    ("sla_risk_alert", "SLA Risk Alert"),
                    ("unassigned_visit_attention", "Unassigned Visit Attention"),
                    ("idle_capacity_opportunity", "Idle Capacity Opportunity"),
                    ("route_efficiency_attention", "Route Efficiency Attention"),
                ],
                db_index=True,
                max_length=30,
            ),
        ),
        migrations.CreateModel(
            name="AgentScheduleHealthFlag",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("schedule_date", models.DateField(blank=True, db_index=True, null=True)),
                ("flag_type", models.CharField(choices=[("technician_overload", "Technician Overload"), ("conflict", "Conflict"), ("sla_risk", "SLA Risk"), ("unassigned_backlog", "Unassigned Backlog"), ("idle_capacity", "Idle Capacity"), ("route_efficiency", "Route Efficiency")], db_index=True, max_length=40)),
                ("status", models.CharField(choices=[("active", "Active"), ("watching", "Watching"), ("resolved", "Resolved")], db_index=True, default="active", max_length=20)),
                ("attention_score", models.PositiveSmallIntegerField(db_index=True, default=0)),
                ("summary", models.CharField(max_length=240)),
                ("risk_level", models.CharField(db_index=True, default="medium", max_length=20)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("last_detected_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("agent", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="schedule_health_flags", to="ai_agents_center.agentdefinition")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="agent_schedule_health_flags", to="companies.company")),
                ("latest_recommendation", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="schedule_health_flags", to="ai_agents_center.agentrecommendation")),
                ("latest_run", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="schedule_health_flags", to="ai_agents_center.agentrun")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="agent_schedule_health_flags", to="smart_system.operationalsite")),
                ("technician", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="agent_schedule_health_flags", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "ai_agents_schedule_health_flags",
                "ordering": ["-attention_score", "-updated_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="agentschedulehealthflag",
            constraint=models.UniqueConstraint(fields=("agent", "company", "technician", "schedule_date", "flag_type"), name="uniq_ai_agents_schedule_health_flag"),
        ),
    ]
