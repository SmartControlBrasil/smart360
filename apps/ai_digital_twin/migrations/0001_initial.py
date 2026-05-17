import uuid

import django.db.models.deletion
from django.db import migrations, models
import django.utils.timezone


def seed_twin_subscriptions(apps, schema_editor):
    EventSubscription = apps.get_model("integration_bus", "EventSubscription")
    subscriptions = [
        ("failures.created", "ai_digital_twin", "twin_projection_refresh"),
        ("work_orders.created", "ai_digital_twin", "twin_projection_refresh"),
        ("work_orders.completed", "ai_digital_twin", "twin_projection_refresh"),
        ("work_orders.delayed", "ai_digital_twin", "twin_projection_refresh"),
        ("preventive.overdue", "ai_digital_twin", "twin_projection_refresh"),
        ("preventive.completed", "ai_digital_twin", "twin_projection_refresh"),
        ("checklists.nok_detected", "ai_digital_twin", "twin_projection_refresh"),
        ("agents.recommendation_created", "ai_digital_twin", "twin_projection_refresh"),
        ("agents.anomaly_detected", "ai_digital_twin", "twin_projection_refresh"),
        ("decision.executed", "ai_digital_twin", "twin_projection_refresh"),
        ("autonomy.execution_completed", "ai_digital_twin", "twin_projection_refresh"),
    ]
    for event_name, target_module, handler_name in subscriptions:
        EventSubscription.objects.update_or_create(
            event_name=event_name,
            target_module=target_module,
            handler_name=handler_name,
            defaults={"is_active": True, "execution_mode": "async", "retry_policy": {"max_retries": 3}},
        )


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0001_initial"),
        ("smart_system", "0001_initial"),
        ("integration_bus", "0002_realtime_event_bus"),
    ]

    operations = [
        migrations.CreateModel(
            name="DigitalTwin",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("twin_type", models.CharField(choices=[("site_operational_twin", "Site Operational Twin"), ("asset_operational_twin", "Asset Operational Twin")], db_index=True, max_length=40)),
                ("external_reference", models.CharField(blank=True, max_length=120)),
                ("status", models.CharField(choices=[("active", "Active"), ("attention", "Attention"), ("critical", "Critical"), ("inactive", "Inactive")], db_index=True, default="active", max_length=20)),
                ("risk_level", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], db_index=True, default="low", max_length=20)),
                ("current_state_summary", models.CharField(blank=True, max_length=255)),
                ("state_payload", models.JSONField(blank=True, default=dict)),
                ("risk_payload", models.JSONField(blank=True, default=dict)),
                ("timeline_payload", models.JSONField(blank=True, default=list)),
                ("summary_payload", models.JSONField(blank=True, default=dict)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("last_projected_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("asset", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="digital_twins", to="smart_system.asset")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="digital_twins", to="companies.company")),
                ("contract", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="digital_twins", to="smart_system.maintenancecontract")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="digital_twins", to="smart_system.operationalsite")),
            ],
            options={"db_table": "ai_digital_twins", "ordering": ["-last_projected_at", "-updated_at"]},
        ),
        migrations.AddIndex(
            model_name="digitaltwin",
            index=models.Index(fields=["company", "twin_type", "risk_level"], name="digital_twin_scope_idx"),
        ),
        migrations.AddIndex(
            model_name="digitaltwin",
            index=models.Index(fields=["site", "asset"], name="digital_twin_entity_idx"),
        ),
        migrations.CreateModel(
            name="DigitalTwinSnapshot",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("snapshot_time", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("state_payload", models.JSONField(blank=True, default=dict)),
                ("risk_payload", models.JSONField(blank=True, default=dict)),
                ("summary", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("digital_twin", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="snapshots", to="ai_digital_twin.digitaltwin")),
            ],
            options={"db_table": "ai_digital_twin_snapshots", "ordering": ["-snapshot_time", "-created_at"]},
        ),
        migrations.CreateModel(
            name="DigitalTwinSignal",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("signal_type", models.CharField(db_index=True, max_length=80)),
                ("source_type", models.CharField(db_index=True, max_length=80)),
                ("source_reference", models.CharField(blank=True, max_length=120)),
                ("severity", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], db_index=True, default="low", max_length=20)),
                ("title", models.CharField(max_length=180)),
                ("summary", models.TextField(blank=True)),
                ("signal_payload", models.JSONField(blank=True, default=dict)),
                ("occurred_at", models.DateTimeField(db_index=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("cleared_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("digital_twin", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="signals", to="ai_digital_twin.digitaltwin")),
            ],
            options={"db_table": "ai_digital_twin_signals", "ordering": ["-occurred_at", "-created_at"]},
        ),
        migrations.AddIndex(
            model_name="digitaltwinsignal",
            index=models.Index(fields=["digital_twin", "is_active", "severity"], name="digital_twin_signal_idx"),
        ),
        migrations.CreateModel(
            name="DigitalTwinProjection",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("projection_type", models.CharField(choices=[("state", "State"), ("risk", "Risk"), ("timeline", "Timeline"), ("insight", "Insight")], db_index=True, max_length=20)),
                ("projection_status", models.CharField(choices=[("active", "Active"), ("stale", "Stale"), ("failed", "Failed")], db_index=True, default="active", max_length=20)),
                ("source_window_start", models.DateTimeField(blank=True, null=True)),
                ("source_window_end", models.DateTimeField(blank=True, null=True)),
                ("projection_payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("digital_twin", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="projections", to="ai_digital_twin.digitaltwin")),
            ],
            options={"db_table": "ai_digital_twin_projections", "ordering": ["projection_type", "-updated_at"]},
        ),
        migrations.AddConstraint(
            model_name="digitaltwinprojection",
            constraint=models.UniqueConstraint(fields=("digital_twin", "projection_type"), name="uniq_digital_twin_projection_type"),
        ),
        migrations.RunPython(seed_twin_subscriptions, migrations.RunPython.noop),
    ]
