from rest_framework.routers import DefaultRouter
from django.urls import path

from .views import (
    AnalyticsDashboardViewSet,
    AnalyticsDimensionViewSet,
    AnalyticsEventViewSet,
    AnalyticsExecutiveOverviewView,
    AnalyticsExecutiveRefreshView,
    AnalyticsAssetsView,
    AnalyticsMetricValueViewSet,
    AnalyticsMetricViewSet,
    AnalyticsProfitabilityView,
    AnalyticsReportViewSet,
    AnalyticsRevenueView,
    AnalyticsSnapshotViewSet,
    AnalyticsTechniciansView,
    AnalyticsWidgetViewSet,
    ClientProfitabilityViewSet,
    ContractProfitabilityViewSet,
    OperationalMetricsViewSet,
    TechnicianPerformanceViewSet,
)

router = DefaultRouter()
router.register("events", AnalyticsEventViewSet, basename="analytics-events")
router.register("metrics", AnalyticsMetricViewSet, basename="analytics-metrics")
router.register("metric-values", AnalyticsMetricValueViewSet, basename="analytics-metric-values")
router.register("dimensions", AnalyticsDimensionViewSet, basename="analytics-dimensions")
router.register("reports", AnalyticsReportViewSet, basename="analytics-reports")
router.register("dashboards", AnalyticsDashboardViewSet, basename="analytics-dashboards")
router.register("widgets", AnalyticsWidgetViewSet, basename="analytics-widgets")
router.register("snapshots", AnalyticsSnapshotViewSet, basename="analytics-snapshots")
router.register("operational-metrics", OperationalMetricsViewSet, basename="analytics-operational-metrics")
router.register("client-profitability", ClientProfitabilityViewSet, basename="analytics-client-profitability")
router.register("contract-profitability", ContractProfitabilityViewSet, basename="analytics-contract-profitability")
router.register("technician-performance", TechnicianPerformanceViewSet, basename="analytics-technician-performance")

urlpatterns = [
    path("executive/overview/", AnalyticsExecutiveOverviewView.as_view(), name="analytics-executive-overview"),
    path("executive/refresh/", AnalyticsExecutiveRefreshView.as_view(), name="analytics-executive-refresh"),
    path("revenue/", AnalyticsRevenueView.as_view(), name="analytics-revenue"),
    path("profitability/", AnalyticsProfitabilityView.as_view(), name="analytics-profitability"),
    path("technicians/", AnalyticsTechniciansView.as_view(), name="analytics-technicians"),
    path("assets/", AnalyticsAssetsView.as_view(), name="analytics-assets"),
] + router.urls
