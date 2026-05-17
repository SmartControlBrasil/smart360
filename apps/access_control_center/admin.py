from django.contrib import admin

from apps.access_control_center.models import (
    AccessAuditLog,
    AccessPolicy,
    PermissionAction,
    PermissionDomain,
    PolicyAssignment,
    Role,
    RolePermission,
    SensitiveActionApproval,
    UserRoleAssignment,
)


class PermissionActionInline(admin.TabularInline):
    model = PermissionAction
    extra = 0


@admin.register(PermissionDomain)
class PermissionDomainAdmin(admin.ModelAdmin):
    list_display = ("name", "module_name", "slug", "is_active", "created_at")
    list_filter = ("module_name", "is_active")
    search_fields = ("name", "slug", "description", "module_name")
    readonly_fields = ("public_id", "created_at")
    inlines = [PermissionActionInline]


@admin.register(PermissionAction)
class PermissionActionAdmin(admin.ModelAdmin):
    list_display = ("action_name", "domain", "is_active", "created_at")
    list_filter = ("domain", "is_active")
    search_fields = ("action_name", "slug", "description", "domain__name")
    readonly_fields = ("public_id", "created_at")


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "role_type", "is_system_role", "is_active", "updated_at")
    list_filter = ("role_type", "is_system_role", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = [RolePermissionInline]


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    list_display = ("role", "permission_domain", "permission_action", "is_allowed", "created_at")
    list_filter = ("is_allowed", "permission_domain", "permission_action")
    search_fields = ("role__name", "permission_domain__name", "permission_action__action_name")
    readonly_fields = ("public_id", "created_at")


@admin.register(UserRoleAssignment)
class UserRoleAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "company", "scope_type", "scope_reference", "is_active", "expires_at")
    list_filter = ("scope_type", "is_active", "company", "role")
    search_fields = ("user__email", "role__name", "company__name", "scope_reference")
    readonly_fields = ("public_id", "assigned_at", "created_at", "updated_at")


@admin.register(AccessPolicy)
class AccessPolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "policy_type", "is_active", "created_at")
    list_filter = ("domain", "policy_type", "is_active")
    search_fields = ("name", "slug", "domain__name")
    readonly_fields = ("public_id", "created_at")


@admin.register(PolicyAssignment)
class PolicyAssignmentAdmin(admin.ModelAdmin):
    list_display = ("policy", "role", "user", "company", "is_active", "assigned_at")
    list_filter = ("is_active", "policy", "role", "company")
    search_fields = ("policy__name", "role__name", "user__email", "company__name")
    readonly_fields = ("public_id", "assigned_at", "created_at")


@admin.register(AccessAuditLog)
class AccessAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "company",
        "site",
        "domain",
        "action",
        "decision",
        "resource_type",
        "resource_id",
        "request_id",
        "created_at",
    )
    list_filter = ("decision", "domain", "action", "company", "site", "origin", "created_at")
    search_fields = (
        "user__email",
        "domain",
        "action",
        "reason",
        "resource_type",
        "resource_id",
        "request_id",
        "correlation_id",
    )
    readonly_fields = ("public_id", "created_at")


@admin.register(SensitiveActionApproval)
class SensitiveActionApprovalAdmin(admin.ModelAdmin):
    list_display = ("domain", "action_name", "requested_by", "approved_by", "status", "created_at", "approved_at")
    list_filter = ("status", "domain", "action_name")
    search_fields = ("action_name", "requested_by__email", "approved_by__email", "domain__name")
    readonly_fields = ("public_id", "created_at", "updated_at", "approved_at")
