from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView

from apps.core.api.views import ApiRootView, HealthCheckDetailsView, HealthCheckView, HealthLiveView, HealthReadyView
from apps.growth_engine.views import receive_n8n_lead
from apps.institutional.sitemaps import StaticViewSitemap

sitemaps = {
    'institutional': StaticViewSitemap,
}

urlpatterns = [
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path("admin/", admin.site.urls),
    path("health/live/", HealthLiveView.as_view(), name="healthcheck-live"),
    path("health/ready/", HealthReadyView.as_view(), name="healthcheck-ready"),
    path("health/", HealthCheckView.as_view(), name="healthcheck"),
    path("health/details/", HealthCheckDetailsView.as_view(), name="healthcheck-details"),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/public/schema/",
        SpectacularAPIView.as_view(urlconf="apps.public_api.urls"),
        name="public-api-schema",
    ),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="swagger-ui",
    ),
    path(
        "api/public/docs/",
        SpectacularSwaggerView.as_view(url_name="public-api-schema"),
        name="public-swagger-ui",
    ),
    path(
        "api/docs/swagger/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="swagger-ui-legacy",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="api-schema"),
        name="redoc",
    ),
    path(
        "api/public/redoc/",
        SpectacularRedocView.as_view(url_name="public-api-schema"),
        name="public-redoc",
    ),
    path(
        "api/docs/redoc/",
        SpectacularRedocView.as_view(url_name="api-schema"),
        name="redoc-legacy",
    ),
    path("api/v1/", ApiRootView.as_view(), name="api-root"),
    path("api/integrations/n8n/leads/", receive_n8n_lead, name="n8n-integration-leads"),
    path("api/v1/core/", include("apps.core.api.urls")),
    path("api/v1/users/", include("apps.users.api.urls")),
    path("api/v1/companies/", include("apps.companies.api.urls")),
    path("api/v1/roles/", include("apps.roles.api.urls")),
    path("api/v1/site-factory/", include("apps.smart_site_factory.api.urls")),
    path("api/v1/growth/", include("apps.growth_engine.api.urls")),
    path("api/v1/caneca-de-garagem/", include("apps.caneca_de_garagem.api.urls")),
    path("api/v1/smart-system/", include("apps.smart_system.api.urls")),
    path("api/v1/marketplace-technicians/", include("apps.marketplace_technicians.api.urls")),
    path("api/v1/marketplace-analytical/", include("apps.marketplace_analytical.api.urls")),
    path("api/v1/knowledge/", include("apps.knowledge_engine.api.urls")),
    path("api/v1/analytics/", include("apps.analytics_platform.api.urls")),
    path("api/v1/integration-bus/", include("apps.integration_bus.api.urls")),
    path("api/v1/billing/", include("apps.billing.api.urls")),
    path("api/v1/notifications/", include("apps.notification_center.api.urls")),
    path("api/v1/auth/", include("apps.identity.api.auth_urls")),
    path("api/v1/identity/", include("apps.identity.api.identity_urls")),
    path("api/v1/backoffice/", include("apps.backoffice.api.urls")),
    path("api/v1/files/", include("apps.files_center.api.urls")),
    path("api/v1/search/", include("apps.global_search.api.urls")),
    path("api/v1/reporting/", include("apps.reporting_center.api.urls")),
    path("api/v1/configuration/", include("apps.configuration_center.api.urls")),
    path("api/v1/scheduling/", include("apps.scheduling_center.api.urls")),
    path("api/v1/access-control/", include("apps.access_control_center.api.urls")),
    path("api/v1/ai/", include("apps.ai_automation_center.api.urls")),
    path("api/v1/ai-agents/", include("apps.ai_agents_center.api.urls")),
    path("api/v1/ai-decisions/", include("apps.ai_decision_engine.api.urls")),
    path("api/v1/ai-simulations/", include("apps.ai_simulation_engine.api.urls")),
    path("api/v1/ai-optimization/", include("apps.ai_optimization_loop.api.urls")),
    path("api/v1/ai-policies/", include("apps.ai_policy_studio.api.urls")),
    path("api/v1/ai-experiments/", include("apps.ai_experimentation_framework.api.urls")),
    path("api/v1/ai-autonomy/", include("apps.ai_autonomous_ops.api.urls")),
    path("api/v1/ai-digital-twins/", include("apps.ai_digital_twin.api.urls")),
    path("api/v1/ai-knowledge-graph/", include("apps.ai_knowledge_graph.api.urls")),
    path("api/v1/ai-voiceops/", include("apps.ai_voice_ops.api.urls")),
    path("api/v1/observability/", include("apps.observability_center.api.urls")),
    path("api/public/v1/", include(("apps.public_api.urls", "public-api"), namespace="public-api")),
    path("portal/", include(("apps.technical_portal.urls", "technical_portal"), namespace="technical_portal")),
    path("marketplace/", include(("apps.marketplace_ecom.urls", "marketplace_ecom"), namespace="marketplace_ecom")),
    # visual_3d: módulo experimental (não está em INSTALLED_APPS). Reativar somente após
    # registrar apps.visual_3d em LOCAL_APPS e adicionar testes de rota mínimos.
    # path("visual-3d/", include(("apps.visual_3d.urls", "visual_3d"), namespace="visual_3d")),
    path("", include(("apps.users.urls", "users"), namespace="users")),
    path("livia/", include(("apps.livia_assistant.urls", "livia_assistant"), namespace="livia_assistant")),
    path("automation/", include(("apps.automation.urls", "automation"), namespace="automation")),
    path(
        "caneca/",
        include(("apps.caneca_de_garagem.urls", "caneca_de_garagem"), namespace="caneca_de_garagem"),
    ),
    path(
        "caneca-de-garagem/",
        include(("apps.caneca_de_garagem.urls", "caneca_de_garagem"), namespace="caneca_de_garagem_public"),
    ),
    path("", include(("apps.institutional.urls", "institutional"), namespace="institutional")),
    path("", include("apps.admin_shell.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
