import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0002_sitemembership"),
        ("observability_center", "0001_initial"),
        ("smart_system", "0002_multitenant_scope"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="errorincident",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="error_incidents",
                to="companies.company",
            ),
        ),
        migrations.AddField(
            model_name="errorincident",
            name="correlation_id",
            field=models.CharField(blank=True, db_index=True, max_length=120),
        ),
        migrations.AddField(
            model_name="errorincident",
            name="request_id",
            field=models.CharField(blank=True, db_index=True, max_length=120),
        ),
        migrations.AddField(
            model_name="errorincident",
            name="request_path",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="errorincident",
            name="site",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="error_incidents",
                to="smart_system.operationalsite",
            ),
        ),
        migrations.AddField(
            model_name="errorincident",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="error_incidents",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="jobexecutiontrace",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="job_execution_traces",
                to="companies.company",
            ),
        ),
        migrations.AddField(
            model_name="jobexecutiontrace",
            name="request_id",
            field=models.CharField(blank=True, db_index=True, max_length=120),
        ),
        migrations.AddField(
            model_name="jobexecutiontrace",
            name="site",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="job_execution_traces",
                to="smart_system.operationalsite",
            ),
        ),
        migrations.AddField(
            model_name="jobexecutiontrace",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="job_execution_traces",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="systemeventlog",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="system_event_logs",
                to="companies.company",
            ),
        ),
        migrations.AddField(
            model_name="systemeventlog",
            name="request_id",
            field=models.CharField(blank=True, db_index=True, max_length=120),
        ),
        migrations.AddField(
            model_name="systemeventlog",
            name="request_method",
            field=models.CharField(blank=True, max_length=12),
        ),
        migrations.AddField(
            model_name="systemeventlog",
            name="request_path",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="systemeventlog",
            name="site",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="system_event_logs",
                to="smart_system.operationalsite",
            ),
        ),
        migrations.AddField(
            model_name="systemeventlog",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="system_event_logs",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.CreateModel(
            name="RequestTrace",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("request_id", models.CharField(db_index=True, max_length=120, unique=True)),
                ("correlation_id", models.CharField(blank=True, db_index=True, max_length=120)),
                ("method", models.CharField(max_length=12)),
                ("path", models.CharField(db_index=True, max_length=255)),
                ("status_code", models.PositiveIntegerField(db_index=True)),
                ("duration_ms", models.PositiveIntegerField(default=0)),
                ("source_module", models.CharField(blank=True, max_length=80)),
                ("ip_address", models.CharField(blank=True, max_length=64)),
                ("query_params", models.JSONField(blank=True, default=dict)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="request_traces",
                        to="companies.company",
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="request_traces",
                        to="smart_system.operationalsite",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="request_traces",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "observability_request_traces",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="requesttrace",
            index=models.Index(fields=["status_code", "created_at"], name="obs_request_status_idx"),
        ),
        migrations.AddIndex(
            model_name="requesttrace",
            index=models.Index(fields=["company", "site", "created_at"], name="obs_request_scope_idx"),
        ),
    ]
