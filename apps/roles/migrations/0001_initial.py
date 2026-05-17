import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("code", models.CharField(max_length=60, unique=True)),
                ("label", models.CharField(max_length=120)),
                (
                    "scope",
                    models.CharField(
                        choices=[("platform", "Platform"), ("company", "Company"), ("team", "Team")],
                        default="company",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("is_system", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "roles", "ordering": ["scope", "label"]},
        ),
    ]
