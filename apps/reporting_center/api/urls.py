from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ExportExecutionViewSet,
    ExportHistoryView,
    ExportProfileViewSet,
    ReportArtifactViewSet,
    ReportHistoryView,
    ReportLogViewSet,
    ReportRequestViewSet,
    ReportTemplateViewSet,
    ReportingRunExportView,
    ReportingRunReportView,
    ScheduledReportViewSet,
)

router = DefaultRouter()
router.register("templates", ReportTemplateViewSet, basename="reporting-templates")
router.register("requests", ReportRequestViewSet, basename="reporting-requests")
router.register("artifacts", ReportArtifactViewSet, basename="reporting-artifacts")
router.register("export-profiles", ExportProfileViewSet, basename="reporting-export-profiles")
router.register("export-executions", ExportExecutionViewSet, basename="reporting-export-executions")
router.register("logs", ReportLogViewSet, basename="reporting-logs")
router.register("scheduled-reports", ScheduledReportViewSet, basename="reporting-scheduled-reports")

urlpatterns = router.urls + [
    path("run-report/", ReportingRunReportView.as_view(), name="reporting-run-report"),
    path("run-export/", ReportingRunExportView.as_view(), name="reporting-run-export"),
    path("report-history/", ReportHistoryView.as_view(), name="reporting-report-history"),
    path("export-history/", ExportHistoryView.as_view(), name="reporting-export-history"),
]

