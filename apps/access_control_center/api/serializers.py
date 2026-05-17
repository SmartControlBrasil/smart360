from rest_framework import serializers

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
from apps.companies.models import Company
from apps.users.models import User


class PermissionDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = PermissionDomain
        fields = [
            "id",
            "public_id",
            "name",
            "slug",
            "description",
            "module_name",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "public_id", "slug", "created_at"]


class PermissionActionSerializer(serializers.ModelSerializer):
    domain_slug = serializers.CharField(source="domain.slug", read_only=True)

    class Meta:
        model = PermissionAction
        fields = [
            "id",
            "public_id",
            "domain",
            "domain_slug",
            "action_name",
            "slug",
            "description",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "public_id", "slug", "created_at", "domain_slug"]


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = [
            "id",
            "public_id",
            "name",
            "slug",
            "role_type",
            "description",
            "is_system_role",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "slug", "created_at", "updated_at"]


class RolePermissionSerializer(serializers.ModelSerializer):
    role_slug = serializers.CharField(source="role.slug", read_only=True)
    permission_domain_slug = serializers.CharField(source="permission_domain.slug", read_only=True)
    permission_action_slug = serializers.CharField(source="permission_action.slug", read_only=True)

    class Meta:
        model = RolePermission
        fields = [
            "id",
            "public_id",
            "role",
            "role_slug",
            "permission_domain",
            "permission_domain_slug",
            "permission_action",
            "permission_action_slug",
            "is_allowed",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "public_id",
            "created_at",
            "role_slug",
            "permission_domain_slug",
            "permission_action_slug",
        ]

    def validate(self, attrs):
        domain = attrs.get("permission_domain", getattr(self.instance, "permission_domain", None))
        action = attrs.get("permission_action", getattr(self.instance, "permission_action", None))
        if domain and action and action.domain_id != domain.id:
            raise serializers.ValidationError(
                {"permission_action": "Selected action must belong to the selected permission domain."}
            )
        return attrs


class UserRoleAssignmentSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source="user.email", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)
    is_current = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserRoleAssignment
        fields = [
            "id",
            "public_id",
            "user",
            "user_email",
            "role",
            "role_name",
            "company",
            "company_name",
            "scope_type",
            "scope_reference",
            "assigned_by",
            "assigned_at",
            "expires_at",
            "is_active",
            "is_current",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "public_id",
            "user_email",
            "role_name",
            "company_name",
            "is_current",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        scope_type = attrs.get("scope_type", getattr(self.instance, "scope_type", None))
        company = attrs.get("company", getattr(self.instance, "company", None))
        scope_reference = attrs.get("scope_reference", getattr(self.instance, "scope_reference", ""))
        if scope_type == UserRoleAssignment.ScopeType.COMPANY and not company:
            raise serializers.ValidationError({"company": "Company is required for company scope."})
        if scope_type in {UserRoleAssignment.ScopeType.MODULE, UserRoleAssignment.ScopeType.RESOURCE} and not scope_reference:
            raise serializers.ValidationError({"scope_reference": "Scope reference is required for module/resource scope."})
        return attrs


class AccessPolicySerializer(serializers.ModelSerializer):
    domain_slug = serializers.CharField(source="domain.slug", read_only=True)

    class Meta:
        model = AccessPolicy
        fields = [
            "id",
            "public_id",
            "name",
            "slug",
            "domain",
            "domain_slug",
            "policy_type",
            "rule_definition_json",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "public_id", "slug", "domain_slug", "created_at"]


class PolicyAssignmentSerializer(serializers.ModelSerializer):
    policy_name = serializers.CharField(source="policy.name", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = PolicyAssignment
        fields = [
            "id",
            "public_id",
            "policy",
            "policy_name",
            "role",
            "role_name",
            "user",
            "user_email",
            "company",
            "company_name",
            "assigned_at",
            "is_active",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "public_id",
            "policy_name",
            "role_name",
            "user_email",
            "company_name",
            "created_at",
        ]

    def validate(self, attrs):
        if not any(
            [
                attrs.get("role", getattr(self.instance, "role", None)),
                attrs.get("user", getattr(self.instance, "user", None)),
                attrs.get("company", getattr(self.instance, "company", None)),
            ]
        ):
            raise serializers.ValidationError("Provide at least one target: role, user or company.")
        return attrs


class AccessAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessAuditLog
        fields = [
            "id",
            "public_id",
            "user",
            "action",
            "domain",
            "resource_type",
            "resource_id",
            "decision",
            "reason",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


class SensitiveActionApprovalSerializer(serializers.ModelSerializer):
    domain_slug = serializers.CharField(source="domain.slug", read_only=True)

    class Meta:
        model = SensitiveActionApproval
        fields = [
            "id",
            "public_id",
            "action_name",
            "domain",
            "domain_slug",
            "requested_by",
            "approved_by",
            "status",
            "request_payload",
            "approved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "domain_slug", "approved_by", "approved_at", "created_at", "updated_at"]


class PermissionCheckSerializer(serializers.Serializer):
    domain_slug = serializers.CharField()
    action_slug = serializers.CharField()
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all(), required=False, allow_null=True)
    module_name = serializers.CharField(required=False, allow_blank=True)
    resource_type = serializers.CharField(required=False, allow_blank=True)
    resource_id = serializers.CharField(required=False, allow_blank=True)
    context = serializers.JSONField(required=False)


class PolicyEvaluationSerializer(serializers.Serializer):
    policy = serializers.PrimaryKeyRelatedField(queryset=AccessPolicy.objects.all())
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all(), required=False, allow_null=True)
    context = serializers.JSONField(required=False)


class EffectivePermissionSerializer(serializers.Serializer):
    domain = serializers.CharField()
    domain_name = serializers.CharField()
    module_name = serializers.CharField()
    action = serializers.CharField()
    action_slug = serializers.CharField()
    roles = serializers.ListField(child=serializers.CharField())
    is_allowed = serializers.BooleanField()
    has_explicit_deny = serializers.BooleanField()
    effective_decision = serializers.CharField()


class MyRolesSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source="role.name", read_only=True)
    role_slug = serializers.CharField(source="role.slug", read_only=True)
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = UserRoleAssignment
        fields = [
            "id",
            "public_id",
            "role",
            "role_name",
            "role_slug",
            "company",
            "company_name",
            "scope_type",
            "scope_reference",
            "assigned_at",
            "expires_at",
            "is_active",
            "is_current",
        ]
        read_only_fields = fields

