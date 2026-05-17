from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0002_sitemembership"),
        ("smart_system", "0005_service_signature"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="FieldExecutionSnapshot",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("sync_state", models.CharField(choices=[("local_pending", "Local Pending"), ("synced", "Synced"), ("conflict", "Conflict"), ("error", "Error")], default="local_pending", max_length=20)),
                ("execution_status", models.CharField(blank=True, max_length=40)),
                ("progress", models.PositiveIntegerField(default=0)),
                ("checklist_payload", models.JSONField(blank=True, default=dict)),
                ("diagnosis_payload", models.JSONField(blank=True, default=dict)),
                ("executed_action_payload", models.JSONField(blank=True, default=dict)),
                ("materials_payload", models.JSONField(blank=True, default=list)),
                ("evidence_payload", models.JSONField(blank=True, default=list)),
                ("finalization_payload", models.JSONField(blank=True, default=dict)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("last_client_event_at", models.DateTimeField(blank=True, null=True)),
                ("last_server_sync_at", models.DateTimeField(blank=True, null=True)),
                ("last_client_operation_id", models.CharField(blank=True, max_length=120)),
                ("last_conflict_code", models.CharField(blank=True, max_length=80)),
                ("last_conflict_message", models.TextField(blank=True)),
                ("local_device_id", models.CharField(blank=True, max_length=120)),
                ("app_version", models.CharField(blank=True, max_length=60)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="field_execution_snapshots", to="companies.company")),
                ("operational_site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="field_execution_snapshots", to="smart_system.operationalsite")),
                ("service_order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="field_execution_snapshots", to="smart_system.serviceorder")),
                ("technician", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="field_execution_snapshots", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "smart_system_field_execution_snapshots",
                "ordering": ["-updated_at"],
                "constraints": [
                    models.UniqueConstraint(fields=("service_order", "technician"), name="uniq_smart_system_field_snapshot_order_technician"),
                ],
            },
        ),
        migrations.CreateModel(
            name="FieldSyncOperation",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("client_operation_id", models.CharField(max_length=120, unique=True)),
                ("action_type", models.CharField(max_length=60)),
                ("operation_order", models.PositiveIntegerField(default=0)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("processed", "Processed"), ("conflict", "Conflict"), ("error", "Error")], default="pending", max_length=20)),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("request_id", models.CharField(blank=True, max_length=80)),
                ("correlation_id", models.CharField(blank=True, max_length=80)),
                ("error_code", models.CharField(blank=True, max_length=80)),
                ("error_message", models.TextField(blank=True)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("result_payload", models.JSONField(blank=True, default=dict)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="field_sync_operations", to="companies.company")),
                ("operational_site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="field_sync_operations", to="smart_system.operationalsite")),
                ("service_order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="field_sync_operations", to="smart_system.serviceorder")),
                ("technician", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="field_sync_operations", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "smart_system_field_sync_operations",
                "ordering": ["status", "created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="fieldsyncoperation",
            index=models.Index(fields=["service_order", "status"], name="smart_field_sync_order_status_idx"),
        ),
        migrations.AddIndex(
            model_name="fieldsyncoperation",
            index=models.Index(fields=["technician", "created_at"], name="smart_field_sync_technician_created_idx"),
        ),
    ]
