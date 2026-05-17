import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class PermissionDomain(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    module_name = models.CharField(max_length=80, db_index=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "access_control_permission_domains"
        ordering = ["module_name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["module_name", "name"], name="uniq_access_permission_domain_name"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.module_name}-{self.name}")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.module_name}:{self.name}"


class PermissionAction(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    domain = models.ForeignKey(
        "access_control_center.PermissionDomain",
        on_delete=models.CASCADE,
        related_name="actions",
    )
    action_name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "access_control_permission_actions"
        ordering = ["domain__module_name", "domain__name", "action_name"]
        constraints = [
            models.UniqueConstraint(fields=["domain", "action_name"], name="uniq_access_domain_action"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.domain.slug}-{self.action_name}")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.domain.slug}:{self.action_name}"


class Role(models.Model):
    class RoleType(models.TextChoices):
        SYSTEM = "system", "System"
        INTERNAL = "internal", "Internal"
        COMPANY = "company", "Company"
        TECHNICIAN = "technician", "Technician"
        CUSTOMER = "customer", "Customer"
        PARTNER = "partner", "Partner"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    role_type = models.CharField(max_length=30, choices=RoleType.choices, default=RoleType.COMPANY)
    description = models.TextField(blank=True)
    is_system_role = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "access_control_roles"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class RolePermission(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    role = models.ForeignKey("access_control_center.Role", on_delete=models.CASCADE, related_name="role_permissions")
    permission_domain = models.ForeignKey(
        "access_control_center.PermissionDomain",
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )
    permission_action = models.ForeignKey(
        "access_control_center.PermissionAction",
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )
    is_allowed = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "access_control_role_permissions"
        ordering = ["role__name", "permission_domain__module_name", "permission_action__action_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission_domain", "permission_action"],
                name="uniq_access_role_permission",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.role} -> {self.permission_domain.slug}:{self.permission_action.action_name}"


class UserRoleAssignment(models.Model):
    class ScopeType(models.TextChoices):
        GLOBAL = "global", "Global"
        COMPANY = "company", "Company"
        MODULE = "module", "Module"
        RESOURCE = "resource", "Resource"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_role_assignments",
    )
    role = models.ForeignKey("access_control_center.Role", on_delete=models.CASCADE, related_name="user_assignments")
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="access_role_assignments",
        null=True,
        blank=True,
    )
    scope_type = models.CharField(max_length=20, choices=ScopeType.choices, default=ScopeType.GLOBAL)
    scope_reference = models.CharField(max_length=255, blank=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_access_roles",
        null=True,
        blank=True,
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "access_control_user_role_assignments"
        ordering = ["user__email", "role__name", "-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role", "company", "scope_type", "scope_reference"],
                name="uniq_access_user_role_scope",
            ),
        ]

    @property
    def is_current(self) -> bool:
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at <= timezone.now():
            return False
        return True

    def __str__(self) -> str:
        return f"{self.user} -> {self.role}"


class AccessPolicy(models.Model):
    class PolicyType(models.TextChoices):
        COMPANY_BOUNDARY = "company_boundary", "Company Boundary"
        ASSIGNMENT_BOUNDARY = "assignment_boundary", "Assignment Boundary"
        OWNERSHIP = "ownership", "Ownership"
        CUSTOM = "custom", "Custom"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    domain = models.ForeignKey(
        "access_control_center.PermissionDomain",
        on_delete=models.CASCADE,
        related_name="policies",
    )
    policy_type = models.CharField(max_length=40, choices=PolicyType.choices, default=PolicyType.CUSTOM)
    rule_definition_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "access_control_policies"
        ordering = ["domain__module_name", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class PolicyAssignment(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    policy = models.ForeignKey("access_control_center.AccessPolicy", on_delete=models.CASCADE, related_name="assignments")
    role = models.ForeignKey(
        "access_control_center.Role",
        on_delete=models.CASCADE,
        related_name="policy_assignments",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="access_policy_assignments",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="access_policy_assignments",
        null=True,
        blank=True,
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "access_control_policy_assignments"
        ordering = ["policy__name", "-assigned_at"]

    def __str__(self) -> str:
        return f"{self.policy} assignment"


class AccessAuditLog(models.Model):
    class Decision(models.TextChoices):
        ALLOW = "allow", "Allow"
        DENY = "deny", "Deny"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="access_audit_logs",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="access_audit_logs",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="access_audit_logs",
        null=True,
        blank=True,
    )
    action = models.CharField(max_length=80, db_index=True)
    domain = models.CharField(max_length=120, db_index=True)
    resource_type = models.CharField(max_length=120, blank=True)
    resource_id = models.CharField(max_length=120, blank=True)
    decision = models.CharField(max_length=10, choices=Decision.choices)
    request_id = models.CharField(max_length=120, blank=True, db_index=True)
    correlation_id = models.CharField(max_length=120, blank=True, db_index=True)
    origin = models.CharField(max_length=80, blank=True)
    reason = models.TextField(blank=True)
    before_state = models.JSONField(default=dict, blank=True)
    after_state = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "access_control_audit_logs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} {self.domain}:{self.action} {self.decision}"


class SensitiveActionApproval(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    action_name = models.CharField(max_length=80, db_index=True)
    domain = models.ForeignKey(
        "access_control_center.PermissionDomain",
        on_delete=models.CASCADE,
        related_name="sensitive_approvals",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sensitive_action_requests",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_sensitive_actions",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    request_payload = models.JSONField(default=dict, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "access_control_sensitive_approvals"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.domain.slug}:{self.action_name} [{self.status}]"
