import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("companies", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("action", models.CharField(max_length=120)),
                ("entity", models.CharField(max_length=120)),
                ("entity_id", models.CharField(max_length=120)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "company",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="audit_logs", to="companies.company"),
                ),
                (
                    "user",
                    models.ForeignKey(blank=True, null=True, on_delete=models.deletion.SET_NULL, related_name="audit_logs", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"db_table": "audit_logs", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["action", "created_at"], name="audit_logs_action_6dc4c0_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["entity", "entity_id"], name="audit_logs_entity_59fa67_idx"),
        ),
    ]
