from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access_control_center.services.access_service import AccessControlService

from ..models import (
    AnalyticsDashboard,
    AnalyticsDimension,
    AnalyticsEvent,
    AnalyticsMetric,
    AnalyticsMetricValue,
    AnalyticsReport,
    AnalyticsSnapshot,
    ClientProfitability,
    ContractProfitability,
    OperationalMetrics,
    TechnicianPerformance,
    AnalyticsWidget,
)
from ..services.analytics_service import ExecutiveAnalyticsService
from .serializers import (
    AnalyticsDashboardSerializer,
    AnalyticsDimensionSerializer,
    AnalyticsEventSerializer,
    AnalyticsMetricSerializer,
    AnalyticsMetricValueSerializer,
    AnalyticsReportSerializer,
    AnalyticsSnapshotSerializer,
    AnalyticsWidgetSerializer,
    ClientProfitabilitySerializer,
    ContractProfitabilitySerializer,
    OperationalMetricsSerializer,
    TechnicianPerformanceSerializer,
)


class AnalyticsAccessPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        action_slug = "manage" if request.method not in permissions.SAFE_METHODS else "view"
        company = ExecutiveAnalyticsService.resolve_company_scope(
            user=request.user,
            company_id=request.query_params.get("company") or request.data.get("company"),
        )
        allowed, _ = AccessControlService.check_permission(
            user=request.user,
            domain_slug=getattr(view, "permission_domain", "analytics_admin"),
            action_slug=getattr(view, "permission_action", action_slug),
            company=company,
            module_name="analytics_platform",
            resource_type="analytics_endpoint",
            resource_id=request.path,
            context={"request_method": request.method},
            log_decision=False,
        )
        return allowed


class AnalyticsBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [AnalyticsAccessPermission]
    permission_domain = "analytics_admin"

    def get_scoped_company(self):
        return ExecutiveAnalyticsService.resolve_company_scope(
            user=self.request.user,
            company_id=self.request.query_params.get("company"),
        )


class AnalyticsEventViewSet(AnalyticsBaseViewSet):
    serializer_class = AnalyticsEventSerializer
    filterset_fields = ("event_type", "source_module", "user", "company")
    search_fields = ("event_type", "source_module", "entity_type", "entity_id", "user__email", "company__name")
    ordering_fields = ("occurred_at", "created_at", "updated_at")

    def get_queryset(self):
        queryset = AnalyticsEvent.objects.select_related("user", "company").all()
        company = self.get_scoped_company()
        if company is not None:
            queryset = queryset.filter(company=company)
        return queryset


class AnalyticsMetricViewSet(AnalyticsBaseViewSet):
    serializer_class = AnalyticsMetricSerializer
    filterset_fields = ("metric_type", "is_active")
    search_fields = ("metric_name", "metric_slug", "description", "unit")
    ordering_fields = ("metric_name", "updated_at", "created_at")
    queryset = AnalyticsMetric.objects.all()


class AnalyticsMetricValueViewSet(AnalyticsBaseViewSet):
    serializer_class = AnalyticsMetricValueSerializer
    filterset_fields = ("metric", "dimension", "reference_date", "source_module")
    search_fields = ("metric__metric_name", "dimension__name", "dimension_value", "source_module")
    ordering_fields = ("calculated_at", "reference_date", "created_at", "updated_at", "value")
    queryset = AnalyticsMetricValue.objects.select_related("metric", "dimension").all()


class AnalyticsDimensionViewSet(AnalyticsBaseViewSet):
    serializer_class = AnalyticsDimensionSerializer
    filterset_fields = ("is_active",)
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "updated_at", "created_at")
    queryset = AnalyticsDimension.objects.all()


class AnalyticsReportViewSet(AnalyticsBaseViewSet):
    serializer_class = AnalyticsReportSerializer
    filterset_fields = ("report_type", "is_active")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "updated_at", "created_at")
    queryset = AnalyticsReport.objects.all()


class AnalyticsDashboardViewSet(AnalyticsBaseViewSet):
    serializer_class = AnalyticsDashboardSerializer
    filterset_fields = ("is_active",)
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "updated_at", "created_at")
    queryset = AnalyticsDashboard.objects.prefetch_related("widgets").all()


class AnalyticsWidgetViewSet(AnalyticsBaseViewSet):
    serializer_class = AnalyticsWidgetSerializer
    filterset_fields = ("dashboard", "widget_type", "metric", "is_active")
    search_fields = ("title", "dashboard__name", "metric__metric_name")
    ordering_fields = ("ordering", "updated_at", "created_at")
    queryset = AnalyticsWidget.objects.select_related("dashboard", "metric").all()


class AnalyticsSnapshotViewSet(AnalyticsBaseViewSet):
    serializer_class = AnalyticsSnapshotSerializer
    filterset_fields = ("snapshot_type", "snapshot_date")
    search_fields = ("snapshot_type",)
    ordering_fields = ("snapshot_date", "created_at", "updated_at")
    queryset = AnalyticsSnapshot.objects.all()


class OperationalMetricsViewSet(AnalyticsBaseViewSet):
    serializer_class = OperationalMetricsSerializer
    filterset_fields = ("company", "period_type", "period_start")
    ordering_fields = ("period_start", "calculated_at", "total_revenue", "total_profit")

    def get_queryset(self):
        queryset = OperationalMetrics.objects.select_related("company").all()
        company = self.get_scoped_company()
        if company is not None:
            queryset = queryset.filter(company=company)
        return queryset


class ClientProfitabilityViewSet(AnalyticsBaseViewSet):
    serializer_class = ClientProfitabilitySerializer
    filterset_fields = ("company", "client", "period_type", "period_start")
    ordering_fields = ("period_start", "profit", "revenue", "margin")

    def get_queryset(self):
        queryset = ClientProfitability.objects.select_related("company", "client").all()
        company = self.get_scoped_company()
        if company is not None:
            queryset = queryset.filter(company=company)
        return queryset


class ContractProfitabilityViewSet(AnalyticsBaseViewSet):
    serializer_class = ContractProfitabilitySerializer
    filterset_fields = ("company", "contract", "period_type", "period_start")
    ordering_fields = ("period_start", "profit", "revenue", "margin")

    def get_queryset(self):
        queryset = ContractProfitability.objects.select_related("company", "contract", "contract__client").all()
        company = self.get_scoped_company()
        if company is not None:
            queryset = queryset.filter(company=company)
        return queryset


class TechnicianPerformanceViewSet(AnalyticsBaseViewSet):
    serializer_class = TechnicianPerformanceSerializer
    filterset_fields = ("company", "technician", "period_type", "period_start")
    ordering_fields = ("period_start", "jobs_completed", "customer_rating", "profit_generated")

    def get_queryset(self):
        queryset = TechnicianPerformance.objects.select_related("company", "technician").all()
        company = self.get_scoped_company()
        if company is not None:
            queryset = queryset.filter(company=company)
        return queryset


class AnalyticsExecutiveOverviewView(APIView):
    permission_classes = [AnalyticsAccessPermission]
    permission_domain = "analytics_admin"

    def get(self, request):
        company = ExecutiveAnalyticsService.resolve_company_scope(user=request.user, company_id=request.query_params.get("company"))
        if company is None:
            return Response({"detail": "Nenhuma empresa autorizada para analytics."}, status=status.HTTP_403_FORBIDDEN)
        payload = ExecutiveAnalyticsService.build_executive_dashboard(
            company=company,
            reference_date=None,
            period_type=request.query_params.get("period_type", OperationalMetrics.PeriodType.MONTHLY),
        )
        return Response(payload)


class AnalyticsRevenueView(APIView):
    permission_classes = [AnalyticsAccessPermission]
    permission_domain = "analytics_admin"

    def get(self, request):
        company = ExecutiveAnalyticsService.resolve_company_scope(user=request.user, company_id=request.query_params.get("company"))
        if company is None:
            return Response({"detail": "Nenhuma empresa autorizada para analytics."}, status=status.HTTP_403_FORBIDDEN)
        return Response(
            {
                "company": {"id": str(company.public_id), "name": company.name},
                "series": ExecutiveAnalyticsService.get_revenue_series(
                    company=company,
                    period_type=request.query_params.get("period_type", OperationalMetrics.PeriodType.MONTHLY),
                ),
            }
        )


class AnalyticsProfitabilityView(APIView):
    permission_classes = [AnalyticsAccessPermission]
    permission_domain = "analytics_admin"

    def get(self, request):
        company = ExecutiveAnalyticsService.resolve_company_scope(user=request.user, company_id=request.query_params.get("company"))
        if company is None:
            return Response({"detail": "Nenhuma empresa autorizada para analytics."}, status=status.HTTP_403_FORBIDDEN)
        return Response(
            ExecutiveAnalyticsService.get_profitability_payload(
                company=company,
                period_type=request.query_params.get("period_type", OperationalMetrics.PeriodType.MONTHLY),
            )
        )


class AnalyticsTechniciansView(APIView):
    permission_classes = [AnalyticsAccessPermission]
    permission_domain = "analytics_admin"

    def get(self, request):
        company = ExecutiveAnalyticsService.resolve_company_scope(user=request.user, company_id=request.query_params.get("company"))
        if company is None:
            return Response({"detail": "Nenhuma empresa autorizada para analytics."}, status=status.HTTP_403_FORBIDDEN)
        return Response(
            ExecutiveAnalyticsService.get_technician_payload(
                company=company,
                period_type=request.query_params.get("period_type", OperationalMetrics.PeriodType.MONTHLY),
            )
        )


class AnalyticsAssetsView(APIView):
    permission_classes = [AnalyticsAccessPermission]
    permission_domain = "analytics_admin"

    def get(self, request):
        company = ExecutiveAnalyticsService.resolve_company_scope(user=request.user, company_id=request.query_params.get("company"))
        if company is None:
            return Response({"detail": "Nenhuma empresa autorizada para analytics."}, status=status.HTTP_403_FORBIDDEN)
        return Response(
            ExecutiveAnalyticsService.get_asset_payload(
                company=company,
                period_type=request.query_params.get("period_type", OperationalMetrics.PeriodType.MONTHLY),
            )
        )


class AnalyticsExecutiveRefreshView(APIView):
    permission_classes = [AnalyticsAccessPermission]
    permission_domain = "analytics_admin"
    permission_action = "manage"

    def post(self, request):
        company = ExecutiveAnalyticsService.resolve_company_scope(user=request.user, company_id=request.data.get("company"))
        if company is None:
            return Response({"detail": "Nenhuma empresa autorizada para analytics."}, status=status.HTTP_403_FORBIDDEN)
        snapshot = ExecutiveAnalyticsService.refresh_company_snapshots(
            company=company,
            period_type=request.data.get("period_type", OperationalMetrics.PeriodType.MONTHLY),
            user=request.user,
        )
        return Response(OperationalMetricsSerializer(snapshot).data, status=status.HTTP_200_OK)
