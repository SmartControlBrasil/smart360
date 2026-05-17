from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.configuration_center.api.serializers import (
    CompanyConfigurationOverrideSerializer,
    ConfigurationAuditLogSerializer,
    EffectiveFlagsSerializer,
    EffectiveSettingsSerializer,
    FeatureFlagScopeSerializer,
    FeatureFlagSerializer,
    ModuleConfigurationProfileSerializer,
    RuntimeToggleSerializer,
    SystemSettingSerializer,
)
from apps.configuration_center.models import (
    CompanyConfigurationOverride,
    ConfigurationAuditLog,
    FeatureFlag,
    FeatureFlagScope,
    ModuleConfigurationProfile,
    RuntimeToggle,
    SystemSetting,
)
from apps.configuration_center.services.configuration_service import (
    ConfigurationAuditService,
    FeatureFlagService,
    SettingResolutionService,
)


class AuditLoggingMixin:
    audit_action_create = ""
    audit_action_update = ""
    setting_key_field = ""
    flag_key_field = ""

    def _extract_key(self, instance):
        if self.setting_key_field:
            return getattr(instance, self.setting_key_field, "")
        if self.flag_key_field:
            return getattr(instance, self.flag_key_field, "")
        return ""

    def perform_create(self, serializer):
        instance = serializer.save()
        ConfigurationAuditService.log(
            action_type=self.audit_action_create,
            changed_by=self.request.user,
            setting_key=getattr(instance, self.setting_key_field, "") if self.setting_key_field else "",
            feature_flag_key=getattr(instance, self.flag_key_field, "") if self.flag_key_field else "",
            new_value=serializer.data,
        )

    def perform_update(self, serializer):
        previous = self.get_serializer(self.get_object()).data
        instance = serializer.save()
        ConfigurationAuditService.log(
            action_type=self.audit_action_update,
            changed_by=self.request.user,
            setting_key=getattr(instance, self.setting_key_field, "") if self.setting_key_field else "",
            feature_flag_key=getattr(instance, self.flag_key_field, "") if self.flag_key_field else "",
            old_value=previous,
            new_value=serializer.data,
        )


class SystemSettingViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["group_name", "module_name", "value_type", "is_active", "is_sensitive"]
    search_fields = ["key", "slug", "description"]
    ordering_fields = ["group_name", "key", "updated_at"]
    audit_action_create = ConfigurationAuditLog.ActionType.SETTING_CREATED
    audit_action_update = ConfigurationAuditLog.ActionType.SETTING_UPDATED
    setting_key_field = "key"


class FeatureFlagViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = FeatureFlag.objects.prefetch_related("scopes").all()
    serializer_class = FeatureFlagSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["module_name", "flag_type", "is_enabled", "is_active"]
    search_fields = ["key", "slug", "description"]
    ordering_fields = ["key", "rollout_percentage", "updated_at"]
    audit_action_create = ConfigurationAuditLog.ActionType.FLAG_CREATED
    audit_action_update = ConfigurationAuditLog.ActionType.FLAG_UPDATED
    flag_key_field = "key"


class FeatureFlagScopeViewSet(viewsets.ModelViewSet):
    queryset = FeatureFlagScope.objects.select_related("feature_flag", "user", "company").all()
    serializer_class = FeatureFlagScopeSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["scope_type", "feature_flag", "user", "company", "module_name", "is_enabled"]
    search_fields = ["feature_flag__key", "module_name", "scope_key"]
    ordering_fields = ["created_at", "updated_at"]


class ConfigurationAuditLogViewSet(viewsets.ModelViewSet):
    queryset = ConfigurationAuditLog.objects.select_related("changed_by").all()
    serializer_class = ConfigurationAuditLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["action_type", "setting_key", "feature_flag_key", "changed_by"]
    search_fields = ["setting_key", "feature_flag_key", "notes"]
    ordering_fields = ["changed_at", "created_at"]


class ModuleConfigurationProfileViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = ModuleConfigurationProfile.objects.all()
    serializer_class = ModuleConfigurationProfileSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["module_name", "is_active"]
    search_fields = ["name", "slug", "description"]
    ordering_fields = ["module_name", "name", "updated_at"]
    audit_action_create = ConfigurationAuditLog.ActionType.PROFILE_UPDATED
    audit_action_update = ConfigurationAuditLog.ActionType.PROFILE_UPDATED


class CompanyConfigurationOverrideViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = CompanyConfigurationOverride.objects.select_related("company").all()
    serializer_class = CompanyConfigurationOverrideSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["company", "setting_key", "is_active"]
    search_fields = ["company__name", "setting_key"]
    ordering_fields = ["created_at", "updated_at"]
    audit_action_create = ConfigurationAuditLog.ActionType.OVERRIDE_UPDATED
    audit_action_update = ConfigurationAuditLog.ActionType.OVERRIDE_UPDATED
    setting_key_field = "setting_key"


class RuntimeToggleViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    queryset = RuntimeToggle.objects.all()
    serializer_class = RuntimeToggleSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["module_name", "is_enabled"]
    search_fields = ["key", "slug", "description", "notes"]
    ordering_fields = ["module_name", "key", "updated_at"]
    audit_action_create = ConfigurationAuditLog.ActionType.TOGGLE_UPDATED
    audit_action_update = ConfigurationAuditLog.ActionType.TOGGLE_UPDATED


class EffectiveSettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = EffectiveSettingsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        settings_data = SettingResolutionService.get_effective_settings(
            module_name=data.get("module_name", ""),
            company=data.get("company"),
        )
        return Response({"count": len(settings_data), "results": settings_data}, status=status.HTTP_200_OK)


class EffectiveFlagsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = EffectiveFlagsSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        flags_data = FeatureFlagService.get_effective_flags(
            user=request.user,
            company=data.get("company"),
            module_name=data.get("module_name", ""),
        )
        return Response(
            {
                "feature_flags_count": len(flags_data["feature_flags"]),
                "runtime_toggles_count": len(flags_data["runtime_toggles"]),
                "feature_flags": flags_data["feature_flags"],
                "runtime_toggles": flags_data["runtime_toggles"],
            },
            status=status.HTTP_200_OK,
        )
