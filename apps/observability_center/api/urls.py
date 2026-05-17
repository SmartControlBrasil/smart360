from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ErrorIncidentViewSet,
    ErrorSummaryView,
    HealthSummaryView,
    JobExecutionTraceViewSet,
    MetricsSummaryView,
    MetricCounterViewSet,
    PlatformObservabilitySummaryView,
    RequestTraceViewSet,
    SystemEventLogViewSet,
)

router = DefaultRouter()
router.register("system-events", SystemEventLogViewSet, basename="observability-system-events")
router.register("error-incidents", ErrorIncidentViewSet, basename="observability-error-incidents")
router.register("metric-counters", MetricCounterViewSet, basename="observability-metric-counters")
router.register("job-traces", JobExecutionTraceViewSet, basename="observability-job-traces")
router.register("request-traces", RequestTraceViewSet, basename="observability-request-traces")

urlpatterns = router.urls + [
    path("health-summary/", HealthSummaryView.as_view(), name="observability-health-summary"),
    path("error-summary/", ErrorSummaryView.as_view(), name="observability-error-summary"),
    path("metrics-summary/", MetricsSummaryView.as_view(), name="observability-metrics-summary"),
    path("platform-summary/", PlatformObservabilitySummaryView.as_view(), name="observability-platform-summary"),
]
