from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.configuration_center.api.views import (
    CompanyConfigurationOverrideViewSet,
    ConfigurationAuditLogViewSet,
    EffectiveFlagsView,
    EffectiveSettingsView,
    FeatureFlagScopeViewSet,
    FeatureFlagViewSet,
    ModuleConfigurationProfileViewSet,
    RuntimeToggleViewSet,
    SystemSettingViewSet,
)

router = DefaultRouter()
router.register("system-settings", SystemSettingViewSet, basename="configuration-system-setting")
router.register("feature-flags", FeatureFlagViewSet, basename="configuration-feature-flag")
router.register("feature-flag-scopes", FeatureFlagScopeViewSet, basename="configuration-feature-flag-scope")
router.register("audit-logs", ConfigurationAuditLogViewSet, basename="configuration-audit-log")
router.register(
    "module-profiles",
    ModuleConfigurationProfileViewSet,
    basename="configuration-module-profile",
)
router.register(
    "company-overrides",
    CompanyConfigurationOverrideViewSet,
    basename="configuration-company-override",
)
router.register("runtime-toggles", RuntimeToggleViewSet, basename="configuration-runtime-toggle")

urlpatterns = [
    path("", include(router.urls)),
    path("effective-settings/", EffectiveSettingsView.as_view(), name="configuration-effective-settings"),
    path("effective-flags/", EffectiveFlagsView.as_view(), name="configuration-effective-flags"),
]

