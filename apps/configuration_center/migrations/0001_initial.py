import django.db.models.deletion
import django.utils.timezone
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
            name="SystemSetting",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("key", models.CharField(max_length=160, unique=True)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("group_name", models.CharField(db_index=True, max_length=120)),
                ("module_name", models.CharField(blank=True, db_index=True, max_length=80)),
                ("description", models.TextField(blank=True)),
                (
                    "value_type",
                    models.CharField(
                        choices=[
                            ("string", "String"),
                            ("number", "Number"),
                            ("boolean", "Boolean"),
                            ("json", "JSON"),
                        ],
                        default="string",
                        max_length=20,
                    ),
                ),
                ("value_string", models.TextField(blank=True)),
                ("value_number", models.DecimalField(blank=True, decimal_places=4, max_digits=18, null=True)),
                ("value_boolean", models.BooleanField(blank=True, null=True)),
                ("value_json", models.JSONField(blank=True, default=dict)),
                ("default_value_json", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("is_sensitive", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "configuration_system_settings", "ordering": ["group_name", "key"]},
        ),
        migrations.CreateModel(
            name="FeatureFlag",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("key", models.CharField(max_length=160, unique=True)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("module_name", models.CharField(blank=True, db_index=True, max_length=80)),
                ("description", models.TextField(blank=True)),
                (
                    "flag_type",
                    models.CharField(
                        choices=[
                            ("boolean", "Boolean"),
                            ("rollout", "Rollout"),
                            ("conditional", "Conditional"),
                        ],
                        default="boolean",
                        max_length=20,
                    ),
                ),
                ("is_enabled", models.BooleanField(default=False)),
                ("rollout_percentage", models.PositiveIntegerField(default=0)),
                ("config_json", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "configuration_feature_flags", "ordering": ["key"]},
        ),
        migrations.CreateModel(
            name="ModuleConfigurationProfile",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("module_name", models.CharField(db_index=True, max_length=80)),
                ("description", models.TextField(blank=True)),
                ("config_json", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "configuration_module_profiles", "ordering": ["module_name", "name"]},
        ),
        migrations.CreateModel(
            name="RuntimeToggle",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("key", models.CharField(max_length=160, unique=True)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("module_name", models.CharField(blank=True, db_index=True, max_length=80)),
                ("description", models.TextField(blank=True)),
                ("is_enabled", models.BooleanField(default=False)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "configuration_runtime_toggles", "ordering": ["module_name", "key"]},
        ),
        migrations.CreateModel(
            name="ConfigurationAuditLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("setting_key", models.CharField(blank=True, db_index=True, max_length=160)),
                ("feature_flag_key", models.CharField(blank=True, db_index=True, max_length=160)),
                (
                    "action_type",
                    models.CharField(
                        choices=[
                            ("setting_created", "Setting Created"),
                            ("setting_updated", "Setting Updated"),
                            ("flag_created", "Flag Created"),
                            ("flag_updated", "Flag Updated"),
                            ("flag_enabled", "Flag Enabled"),
                            ("flag_disabled", "Flag Disabled"),
                            ("rollout_changed", "Rollout Changed"),
                            ("profile_updated", "Profile Updated"),
                            ("override_updated", "Override Updated"),
                            ("toggle_updated", "Toggle Updated"),
                        ],
                        max_length=40,
                    ),
                ),
                ("old_value_json", models.JSONField(blank=True, default=dict)),
                ("new_value_json", models.JSONField(blank=True, default=dict)),
                ("notes", models.TextField(blank=True)),
                ("changed_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "changed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="configuration_audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "configuration_audit_logs", "ordering": ["-changed_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="CompanyConfigurationOverride",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("setting_key", models.CharField(db_index=True, max_length=160)),
                ("override_value_json", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="configuration_overrides",
                        to="companies.company",
                    ),
                ),
            ],
            options={"db_table": "configuration_company_overrides", "ordering": ["company__name", "setting_key"]},
        ),
        migrations.CreateModel(
            name="FeatureFlagScope",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "scope_type",
                    models.CharField(
                        choices=[
                            ("user", "User"),
                            ("company", "Company"),
                            ("module", "Module"),
                            ("key", "Key"),
                        ],
                        default="company",
                        max_length=20,
                    ),
                ),
                ("module_name", models.CharField(blank=True, max_length=80)),
                ("scope_key", models.CharField(blank=True, max_length=120)),
                ("is_enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feature_flag_scopes",
                        to="companies.company",
                    ),
                ),
                (
                    "feature_flag",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scopes",
                        to="configuration_center.featureflag",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feature_flag_scopes",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "configuration_feature_flag_scopes",
                "ordering": ["feature_flag__key", "scope_type", "-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="systemsetting",
            index=models.Index(fields=["module_name", "is_active"], name="cfg_setting_module_active_idx"),
        ),
        migrations.AddIndex(
            model_name="featureflag",
            index=models.Index(fields=["module_name", "is_active"], name="cfg_flag_module_active_idx"),
        ),
        migrations.AddConstraint(
            model_name="companyconfigurationoverride",
            constraint=models.UniqueConstraint(
                fields=("company", "setting_key"),
                name="uniq_company_setting_override",
            ),
        ),
    ]

