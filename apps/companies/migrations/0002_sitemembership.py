import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("smart_system", "0001_initial"),
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteMembership",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("status", models.CharField(choices=[("active", "Ativo"), ("inactive", "Inativo")], default="active", max_length=20)),
                ("is_primary", models.BooleanField(default=False)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="site_memberships", to="companies.company"),
                ),
                (
                    "site",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="site_memberships", to="smart_system.operationalsite"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="site_memberships", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={
                "db_table": "company_site_memberships",
                "ordering": ["company__name", "site__name", "user__email"],
            },
        ),
        migrations.AddConstraint(
            model_name="sitemembership",
            constraint=models.UniqueConstraint(fields=("user", "site"), name="uniq_user_site_membership"),
        ),
    ]
