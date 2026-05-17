import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("roles", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Company",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("legal_name", models.CharField(blank=True, max_length=200)),
                ("slug", models.SlugField(max_length=180, unique=True)),
                ("tax_id", models.CharField(blank=True, max_length=30)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone_number", models.CharField(blank=True, max_length=30)),
                ("website", models.URLField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Ativa"), ("inactive", "Inativa"), ("suspended", "Suspensa")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "companies", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Membership",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Ativo"), ("invited", "Convidado"), ("inactive", "Inativo")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("is_primary", models.BooleanField(default=False)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("invited_at", models.DateTimeField(blank=True, null=True)),
                ("joined_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="memberships", to="companies.company"),
                ),
                (
                    "roles",
                    models.ManyToManyField(blank=True, related_name="memberships", to="roles.role"),
                ),
                (
                    "user",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="memberships", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"db_table": "company_memberships", "ordering": ["company__name", "user__email"]},
        ),
        migrations.AddConstraint(
            model_name="membership",
            constraint=models.UniqueConstraint(fields=("user", "company"), name="uniq_user_company_membership"),
        ),
    ]
