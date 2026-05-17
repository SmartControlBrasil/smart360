import django.utils.timezone
import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("first_name", models.CharField(max_length=100)),
                ("last_name", models.CharField(blank=True, max_length=100)),
                ("display_name", models.CharField(blank=True, max_length=150)),
                ("phone_number", models.CharField(blank=True, max_length=30)),
                ("job_title", models.CharField(blank=True, max_length=120)),
                ("department", models.CharField(blank=True, max_length=120)),
                (
                    "user_type",
                    models.CharField(
                        choices=[("internal", "Interno"), ("client", "Cliente"), ("partner", "Parceiro")],
                        default="internal",
                        max_length=20,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("is_staff", models.BooleanField(default=False)),
                ("is_verified", models.BooleanField(default=False)),
                ("last_login_at", models.DateTimeField(blank=True, null=True)),
                ("date_joined", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            options={"db_table": "users", "ordering": ["email"]},
        ),
    ]
