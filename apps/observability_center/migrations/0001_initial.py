from django.db import migrations, models
import django.utils.timezone
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ErrorIncident",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("incident_key", models.CharField(max_length=180, unique=True)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                ("error_type", models.CharField(db_index=True, max_length=120)),
                ("severity", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], db_index=True, default="medium", max_length=20)),
                ("message", models.CharField(max_length=255)),
                ("traceback_text", models.TextField(blank=True)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("open", "Open"), ("acknowledged", "Acknowledged"), ("resolved", "Resolved"), ("ignored", "Ignored")], db_index=True, default="open", max_length=20)),
                ("first_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_seen_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("occurrences_count", models.PositiveIntegerField(default=1)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "observability_error_incidents", "ordering": ["-last_seen_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="JobExecutionTrace",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("job_name", models.CharField(db_index=True, max_length=160)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                ("correlation_id", models.CharField(blank=True, db_index=True, max_length=120)),
                ("status", models.CharField(choices=[("started", "Started"), ("completed", "Completed"), ("failed", "Failed"), ("cancelled", "Cancelled")], db_index=True, default="started", max_length=20)),
                ("started_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("duration_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "observability_job_execution_traces", "ordering": ["-started_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="MetricCounter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("metric_key", models.CharField(db_index=True, max_length=140)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                ("value", models.BigIntegerField(default=0)),
                ("period_type", models.CharField(choices=[("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly"), ("total", "Total")], default="daily", max_length=20)),
                ("reference_date", models.DateField(db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "observability_metric_counters", "ordering": ["-reference_date", "metric_key"]},
        ),
        migrations.CreateModel(
            name="SystemEventLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("event_type", models.CharField(db_index=True, max_length=140)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                ("severity", models.CharField(choices=[("info", "Info"), ("warning", "Warning"), ("error", "Error"), ("critical", "Critical")], db_index=True, default="info", max_length=20)),
                ("entity_type", models.CharField(blank=True, max_length=80)),
                ("entity_id", models.CharField(blank=True, max_length=120)),
                ("correlation_id", models.CharField(blank=True, db_index=True, max_length=120)),
                ("message", models.CharField(max_length=255)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "observability_system_event_logs", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="metriccounter",
            constraint=models.UniqueConstraint(fields=("metric_key", "source_module", "period_type", "reference_date"), name="uniq_obs_metric_counter_scope"),
        ),
        migrations.AddIndex(
            model_name="systemeventlog",
            index=models.Index(fields=["source_module", "event_type"], name="obs_event_src_type_idx"),
        ),
        migrations.AddIndex(
            model_name="systemeventlog",
            index=models.Index(fields=["severity", "created_at"], name="obs_event_severity_idx"),
        ),
    ]
