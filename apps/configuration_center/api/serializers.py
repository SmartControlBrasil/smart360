from rest_framework import serializers

from apps.companies.models import Company
from apps.configuration_center.models import (
    CompanyConfigurationOverride,
    ConfigurationAuditLog,
    FeatureFlag,
    FeatureFlagScope,
    ModuleConfigurationProfile,
    RuntimeToggle,
    SystemSetting,
)


class SystemSettingSerializer(serializers.ModelSerializer):
    resolved_value = serializers.SerializerMethodField()

    class Meta:
        model = SystemSetting
        fields = [
            "id",
            "public_id",
            "key",
            "slug",
            "group_name",
            "module_name",
            "description",
            "value_type",
            "value_string",
            "value_number",
            "value_boolean",
            "value_json",
            "default_value_json",
            "resolved_value",
            "is_active",
            "is_sensitive",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "slug", "created_at", "updated_at", "resolved_value"]

    def get_resolved_value(self, obj):
        return obj.resolved_value

    def validate(self, attrs):
        value_type = attrs.get("value_type", getattr(self.instance, "value_type", None))
        has_string = bool(attrs.get("value_string", getattr(self.instance, "value_string", "")))
        has_number = attrs.get("value_number", getattr(self.instance, "value_number", None)) is not None
        has_boolean = attrs.get("value_boolean", getattr(self.instance, "value_boolean", None)) is not None
        has_json = bool(attrs.get("value_json", getattr(self.instance, "value_json", {})))

        validations = {
            SystemSetting.ValueType.STRING: has_string,
            SystemSetting.ValueType.NUMBER: has_number,
            SystemSetting.ValueType.BOOLEAN: has_boolean,
            SystemSetting.ValueType.JSON: has_json,
        }
        if value_type and not validations.get(value_type, False):
            raise serializers.ValidationError({"value_type": "Provide a value compatible with the selected value_type."})
        return attrs


class FeatureFlagScopeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeatureFlagScope
        fields = [
            "id",
            "public_id",
            "feature_flag",
            "scope_type",
            "user",
            "company",
            "module_name",
            "scope_key",
            "is_enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]

    def validate(self, attrs):
        scope_type = attrs.get("scope_type", getattr(self.instance, "scope_type", None))
        if scope_type == FeatureFlagScope.ScopeType.USER and not attrs.get("user", getattr(self.instance, "user", None)):
            raise serializers.ValidationError({"user": "User is required for user scope."})
        if scope_type == FeatureFlagScope.ScopeType.COMPANY and not attrs.get(
            "company", getattr(self.instance, "company", None)
        ):
            raise serializers.ValidationError({"company": "Company is required for company scope."})
        if scope_type == FeatureFlagScope.ScopeType.MODULE and not attrs.get(
            "module_name", getattr(self.instance, "module_name", "")
        ):
            raise serializers.ValidationError({"module_name": "Module name is required for module scope."})
        if scope_type == FeatureFlagScope.ScopeType.KEY and not attrs.get(
            "scope_key", getattr(self.instance, "scope_key", "")
        ):
            raise serializers.ValidationError({"scope_key": "Scope key is required for key scope."})
        return attrs


class FeatureFlagSerializer(serializers.ModelSerializer):
    scopes = FeatureFlagScopeSerializer(many=True, read_only=True)

    class Meta:
        model = FeatureFlag
        fields = [
            "id",
            "public_id",
            "key",
            "slug",
            "module_name",
            "description",
            "flag_type",
            "is_enabled",
            "rollout_percentage",
            "config_json",
            "is_active",
            "scopes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "slug", "created_at", "updated_at", "scopes"]


class ConfigurationAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfigurationAuditLog
        fields = [
            "id",
            "public_id",
            "changed_by",
            "setting_key",
            "feature_flag_key",
            "action_type",
            "old_value_json",
            "new_value_json",
            "notes",
            "changed_at",
            "created_at",
        ]
        read_only_fields = ["id", "public_id", "created_at"]


class ModuleConfigurationProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleConfigurationProfile
        fields = [
            "id",
            "public_id",
            "name",
            "slug",
            "module_name",
            "description",
            "config_json",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "slug", "created_at", "updated_at"]


class CompanyConfigurationOverrideSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = CompanyConfigurationOverride
        fields = [
            "id",
            "public_id",
            "company",
            "company_name",
            "setting_key",
            "override_value_json",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "company_name", "created_at", "updated_at"]


class RuntimeToggleSerializer(serializers.ModelSerializer):
    is_currently_enabled = serializers.SerializerMethodField()

    class Meta:
        model = RuntimeToggle
        fields = [
            "id",
            "public_id",
            "key",
            "slug",
            "module_name",
            "description",
            "is_enabled",
            "is_currently_enabled",
            "expires_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "slug", "created_at", "updated_at", "is_currently_enabled"]

    def get_is_currently_enabled(self, obj):
        return obj.is_currently_enabled


class EffectiveSettingsSerializer(serializers.Serializer):
    module_name = serializers.CharField(required=False, allow_blank=True)
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all(), required=False)


class EffectiveFlagsSerializer(serializers.Serializer):
    module_name = serializers.CharField(required=False, allow_blank=True)
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all(), required=False)
