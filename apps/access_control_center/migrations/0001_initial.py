import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="PermissionDomain",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(blank=True, max_length=140, unique=True)),
                ("description", models.TextField(blank=True)),
                ("module_name", models.CharField(db_index=True, max_length=80)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "access_control_permission_domains",
                "ordering": ["module_name", "name"],
            },
        ),
        migrations.CreateModel(
            name="Role",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(blank=True, max_length=140, unique=True)),
                (
                    "role_type",
                    models.CharField(
                        choices=[
                            ("system", "System"),
                            ("internal", "Internal"),
                            ("company", "Company"),
                            ("technician", "Technician"),
                            ("customer", "Customer"),
                            ("partner", "Partner"),
                        ],
                        default="company",
                        max_length=30,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("is_system_role", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "access_control_roles", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="AccessAuditLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("action", models.CharField(db_index=True, max_length=80)),
                ("domain", models.CharField(db_index=True, max_length=120)),
                ("resource_type", models.CharField(blank=True, max_length=120)),
                ("resource_id", models.CharField(blank=True, max_length=120)),
                ("decision", models.CharField(choices=[("allow", "Allow"), ("deny", "Deny")], max_length=10)),
                ("reason", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="access_audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "access_control_audit_logs", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AccessPolicy",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=140)),
                ("slug", models.SlugField(blank=True, max_length=160, unique=True)),
                (
                    "policy_type",
                    models.CharField(
                        choices=[
                            ("company_boundary", "Company Boundary"),
                            ("assignment_boundary", "Assignment Boundary"),
                            ("ownership", "Ownership"),
                            ("custom", "Custom"),
                        ],
                        default="custom",
                        max_length=40,
                    ),
                ),
                ("rule_definition_json", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "domain",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="policies",
                        to="access_control_center.permissiondomain",
                    ),
                ),
            ],
            options={"db_table": "access_control_policies", "ordering": ["domain__module_name", "name"]},
        ),
        migrations.CreateModel(
            name="PermissionAction",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("action_name", models.CharField(max_length=80)),
                ("slug", models.SlugField(blank=True, max_length=160, unique=True)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "domain",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="actions",
                        to="access_control_center.permissiondomain",
                    ),
                ),
            ],
            options={
                "db_table": "access_control_permission_actions",
                "ordering": ["domain__module_name", "domain__name", "action_name"],
            },
        ),
        migrations.CreateModel(
            name="SensitiveActionApproval",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("action_name", models.CharField(db_index=True, max_length=80)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("cancelled", "Cancelled"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("request_payload", models.JSONField(blank=True, default=dict)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="approved_sensitive_actions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "domain",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sensitive_approvals",
                        to="access_control_center.permissiondomain",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sensitive_action_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "access_control_sensitive_approvals", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="RolePermission",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("is_allowed", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "permission_action",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_permissions",
                        to="access_control_center.permissionaction",
                    ),
                ),
                (
                    "permission_domain",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_permissions",
                        to="access_control_center.permissiondomain",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_permissions",
                        to="access_control_center.role",
                    ),
                ),
            ],
            options={
                "db_table": "access_control_role_permissions",
                "ordering": ["role__name", "permission_domain__module_name", "permission_action__action_name"],
            },
        ),
        migrations.CreateModel(
            name="PolicyAssignment",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("assigned_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_policy_assignments",
                        to="companies.company",
                    ),
                ),
                (
                    "policy",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignments",
                        to="access_control_center.accesspolicy",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="policy_assignments",
                        to="access_control_center.role",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_policy_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "access_control_policy_assignments", "ordering": ["policy__name", "-assigned_at"]},
        ),
        migrations.CreateModel(
            name="UserRoleAssignment",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "scope_type",
                    models.CharField(
                        choices=[
                            ("global", "Global"),
                            ("company", "Company"),
                            ("module", "Module"),
                            ("resource", "Resource"),
                        ],
                        default="global",
                        max_length=20,
                    ),
                ),
                ("scope_reference", models.CharField(blank=True, max_length=255)),
                ("assigned_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assigned_access_roles",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_role_assignments",
                        to="companies.company",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_assignments",
                        to="access_control_center.role",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_role_assignments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "access_control_user_role_assignments",
                "ordering": ["user__email", "role__name", "-assigned_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="permissiondomain",
            constraint=models.UniqueConstraint(fields=("module_name", "name"), name="uniq_access_permission_domain_name"),
        ),
        migrations.AddConstraint(
            model_name="permissionaction",
            constraint=models.UniqueConstraint(fields=("domain", "action_name"), name="uniq_access_domain_action"),
        ),
        migrations.AddConstraint(
            model_name="rolepermission",
            constraint=models.UniqueConstraint(
                fields=("role", "permission_domain", "permission_action"),
                name="uniq_access_role_permission",
            ),
        ),
        migrations.AddConstraint(
            model_name="userroleassignment",
            constraint=models.UniqueConstraint(
                fields=("user", "role", "company", "scope_type", "scope_reference"),
                name="uniq_access_user_role_scope",
            ),
        ),
    ]

