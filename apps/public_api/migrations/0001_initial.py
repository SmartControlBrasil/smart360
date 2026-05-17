import uuid
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0002_sitemembership"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="IntegrationCredential",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=140)),
                ("key_prefix", models.CharField(editable=False, max_length=24, unique=True)),
                ("secret_hash", models.CharField(blank=True, max_length=255)),
                ("allowed_scopes", models.JSONField(blank=True, default=list)),
                ("allowed_ips", models.JSONField(blank=True, default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="integration_credentials", to="companies.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_integration_credentials", to=settings.AUTH_USER_MODEL)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="integration_credentials", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "public_api_integration_credentials", "ordering": ["name"]},
        ),
    ]
