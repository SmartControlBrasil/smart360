from django.contrib import admin

from apps.configuration_center.models import (
    CompanyConfigurationOverride,
    ConfigurationAuditLog,
    FeatureFlag,
    FeatureFlagScope,
    ModuleConfigurationProfile,
    RuntimeToggle,
    SystemSetting,
)


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = (
        "key",
        "group_name",
        "module_name",
        "value_type",
        "is_active",
        "is_sensitive",
        "updated_at",
    )
    list_filter = ("group_name", "module_name", "value_type", "is_active", "is_sensitive")
    search_fields = ("key", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


class FeatureFlagScopeInline(admin.TabularInline):
    model = FeatureFlagScope
    extra = 0


@admin.register(FeatureFlag)
class FeatureFlagAdmin(admin.ModelAdmin):
    list_display = (
        "key",
        "module_name",
        "flag_type",
        "is_enabled",
        "rollout_percentage",
        "is_active",
        "updated_at",
    )
    list_filter = ("module_name", "flag_type", "is_enabled", "is_active")
    search_fields = ("key", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = [FeatureFlagScopeInline]


@admin.register(FeatureFlagScope)
class FeatureFlagScopeAdmin(admin.ModelAdmin):
    list_display = ("feature_flag", "scope_type", "user", "company", "module_name", "scope_key", "is_enabled")
    list_filter = ("scope_type", "is_enabled", "module_name")
    search_fields = ("feature_flag__key", "module_name", "scope_key", "user__email", "company__name")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(ConfigurationAuditLog)
class ConfigurationAuditLogAdmin(admin.ModelAdmin):
    list_display = ("action_type", "setting_key", "feature_flag_key", "changed_by", "changed_at")
    list_filter = ("action_type", "changed_at")
    search_fields = ("setting_key", "feature_flag_key", "notes", "changed_by__email")
    readonly_fields = ("public_id", "created_at", "changed_at")


@admin.register(ModuleConfigurationProfile)
class ModuleConfigurationProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "module_name", "is_active", "updated_at")
    list_filter = ("module_name", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(CompanyConfigurationOverride)
class CompanyConfigurationOverrideAdmin(admin.ModelAdmin):
    list_display = ("company", "setting_key", "is_active", "updated_at")
    list_filter = ("is_active", "company")
    search_fields = ("company__name", "setting_key")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(RuntimeToggle)
class RuntimeToggleAdmin(admin.ModelAdmin):
    list_display = ("key", "module_name", "is_enabled", "expires_at", "updated_at")
    list_filter = ("module_name", "is_enabled")
    search_fields = ("key", "slug", "description", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")

