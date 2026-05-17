from __future__ import annotations

from typing import Any

from apps.configuration_center.models import (
    CompanyConfigurationOverride,
    ConfigurationAuditLog,
    FeatureFlag,
    FeatureFlagScope,
    RuntimeToggle,
    SystemSetting,
)


class ConfigurationAuditService:
    @staticmethod
    def log(
        *,
        action_type: str,
        changed_by=None,
        setting_key: str = "",
        feature_flag_key: str = "",
        old_value: Any = None,
        new_value: Any = None,
        notes: str = "",
    ) -> ConfigurationAuditLog:
        return ConfigurationAuditLog.objects.create(
            action_type=action_type,
            changed_by=changed_by,
            setting_key=setting_key,
            feature_flag_key=feature_flag_key,
            old_value_json=old_value if isinstance(old_value, dict) else {"value": old_value},
            new_value_json=new_value if isinstance(new_value, dict) else {"value": new_value},
            notes=notes,
        )


class SettingResolutionService:
    @staticmethod
    def _serialize_setting(setting: SystemSetting) -> dict[str, Any]:
        return {
            "key": setting.key,
            "group_name": setting.group_name,
            "module_name": setting.module_name,
            "value_type": setting.value_type,
            "value": setting.resolved_value,
            "default_value": setting.default_value_json,
            "is_sensitive": setting.is_sensitive,
        }

    @classmethod
    def get_effective_settings(cls, *, module_name: str = "", company=None) -> list[dict[str, Any]]:
        queryset = SystemSetting.objects.filter(is_active=True)
        if module_name:
            queryset = queryset.filter(module_name__in=["", module_name])

        settings_map = {setting.key: cls._serialize_setting(setting) for setting in queryset}

        if company is not None:
            overrides = CompanyConfigurationOverride.objects.filter(company=company, is_active=True)
            for override in overrides:
                if override.setting_key in settings_map:
                    settings_map[override.setting_key]["value"] = override.override_value_json
                    settings_map[override.setting_key]["company_override"] = True

        return list(settings_map.values())


class FeatureFlagService:
    @staticmethod
    def _apply_scope(flag_data: dict[str, Any], scope: FeatureFlagScope) -> None:
        flag_data["is_enabled"] = scope.is_enabled
        flag_data.setdefault("applied_scopes", []).append(
            {
                "scope_type": scope.scope_type,
                "module_name": scope.module_name,
                "scope_key": scope.scope_key,
                "user_id": scope.user_id,
                "company_id": scope.company_id,
                "is_enabled": scope.is_enabled,
            }
        )

    @classmethod
    def get_effective_flags(cls, *, user=None, company=None, module_name: str = "") -> dict[str, list[dict[str, Any]]]:
        queryset = FeatureFlag.objects.filter(is_active=True)
        if module_name:
            queryset = queryset.filter(module_name__in=["", module_name])

        flag_map: dict[int, dict[str, Any]] = {}
        for flag in queryset:
            flag_map[flag.id] = {
                "key": flag.key,
                "module_name": flag.module_name,
                "flag_type": flag.flag_type,
                "is_enabled": flag.is_enabled,
                "rollout_percentage": flag.rollout_percentage,
                "config": flag.config_json,
            }

        scopes = FeatureFlagScope.objects.filter(feature_flag__in=queryset).select_related("user", "company")
        for scope in scopes:
            if scope.scope_type == FeatureFlagScope.ScopeType.USER and user and scope.user_id == user.id:
                cls._apply_scope(flag_map[scope.feature_flag_id], scope)
            elif scope.scope_type == FeatureFlagScope.ScopeType.COMPANY and company and scope.company_id == company.id:
                cls._apply_scope(flag_map[scope.feature_flag_id], scope)
            elif scope.scope_type == FeatureFlagScope.ScopeType.MODULE and module_name and scope.module_name == module_name:
                cls._apply_scope(flag_map[scope.feature_flag_id], scope)
            elif scope.scope_type == FeatureFlagScope.ScopeType.KEY and scope.scope_key:
                cls._apply_scope(flag_map[scope.feature_flag_id], scope)

        toggles = RuntimeToggle.objects.filter(is_enabled=True)
        if module_name:
            toggles = toggles.filter(module_name__in=["", module_name])

        toggle_data = [
            {
                "key": toggle.key,
                "module_name": toggle.module_name,
                "is_enabled": toggle.is_currently_enabled,
                "expires_at": toggle.expires_at,
            }
            for toggle in toggles
        ]

        return {
            "feature_flags": list(flag_map.values()),
            "runtime_toggles": toggle_data,
        }
