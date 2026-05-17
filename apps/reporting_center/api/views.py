from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import (
    ExportExecution,
    ExportProfile,
    ReportArtifact,
    ReportLog,
    ReportRequest,
    ReportTemplate,
    ScheduledReport,
)
from ..services.reporting_service import ExportExecutionService, ReportGenerationService
from .serializers import (
    ExportExecutionSerializer,
    ExportProfileSerializer,
    ReportArtifactSerializer,
    ReportLogSerializer,
    ReportRequestSerializer,
    ReportTemplateSerializer,
    ScheduledReportSerializer,
)


class ReportingBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class ReportTemplateViewSet(ReportingBaseViewSet):
    queryset = ReportTemplate.objects.all()
    serializer_class = ReportTemplateSerializer
    filterset_fields = ("source_module", "report_type", "output_format_default", "is_active")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "created_at", "updated_at")


class ReportRequestViewSet(ReportingBaseViewSet):
    queryset = ReportRequest.objects.select_related("template", "requested_by", "requested_for_company").all()
    serializer_class = ReportRequestSerializer
    filterset_fields = ("template", "requested_by", "requested_for_company", "source_module", "status", "output_format")
    search_fields = ("template__name", "error_message")
    ordering_fields = ("created_at", "started_at", "completed_at", "updated_at")

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        report_request = self.get_object()
        report_request, artifact = ReportGenerationService.run_report(report_request=report_request)
        return Response(
            {
                "report_request": ReportRequestSerializer(report_request).data,
                "artifact": ReportArtifactSerializer(artifact).data,
            },
            status=status.HTTP_200_OK,
        )


class ReportArtifactViewSet(ReportingBaseViewSet):
    queryset = ReportArtifact.objects.select_related("report_request").all()
    serializer_class = ReportArtifactSerializer
    filterset_fields = ("report_request", "artifact_type", "mime_type")
    search_fields = ("file_name", "storage_path")
    ordering_fields = ("generated_at", "created_at", "updated_at")


class ExportProfileViewSet(ReportingBaseViewSet):
    queryset = ExportProfile.objects.select_related("created_by").all()
    serializer_class = ExportProfileSerializer
    filterset_fields = ("source_module", "export_type", "is_active", "created_by")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "created_at", "updated_at")


class ExportExecutionViewSet(ReportingBaseViewSet):
    queryset = ExportExecution.objects.select_related("export_profile", "requested_by").all()
    serializer_class = ExportExecutionSerializer
    filterset_fields = ("export_profile", "requested_by", "status", "output_format")
    search_fields = ("export_profile__name", "error_message")
    ordering_fields = ("created_at", "started_at", "completed_at", "updated_at")

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        export_execution = self.get_object()
        export_execution = ExportExecutionService.run_export(export_execution=export_execution)
        return Response(self.get_serializer(export_execution).data, status=status.HTTP_200_OK)


class ReportLogViewSet(ReportingBaseViewSet):
    queryset = ReportLog.objects.select_related("report_request", "export_execution").all()
    serializer_class = ReportLogSerializer
    filterset_fields = ("source_module", "report_request", "export_execution", "log_level")
    search_fields = ("message",)
    ordering_fields = ("created_at", "updated_at")


class ScheduledReportViewSet(ReportingBaseViewSet):
    queryset = ScheduledReport.objects.select_related("template", "owner_user", "owner_company").all()
    serializer_class = ScheduledReportSerializer
    filterset_fields = ("template", "owner_user", "owner_company", "schedule_type", "output_format", "is_active")
    search_fields = ("name", "slug")
    ordering_fields = ("name", "last_run_at", "created_at", "updated_at")


class ReportingRunReportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ReportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report_request = serializer.save(requested_by=request.user)
        report_request, artifact = ReportGenerationService.run_report(report_request=report_request)
        return Response(
            {
                "report_request": ReportRequestSerializer(report_request).data,
                "artifact": ReportArtifactSerializer(artifact).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ReportingRunExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ExportExecutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        export_execution = serializer.save(requested_by=request.user)
        export_execution = ExportExecutionService.run_export(export_execution=export_execution)
        return Response(ExportExecutionSerializer(export_execution).data, status=status.HTTP_201_CREATED)


class ReportHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        queryset = ReportRequest.objects.select_related("template", "requested_by").order_by("-created_at")[:50]
        return Response(ReportRequestSerializer(queryset, many=True).data, status=status.HTTP_200_OK)


class ExportHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        queryset = ExportExecution.objects.select_related("export_profile", "requested_by").order_by("-created_at")[:50]
        return Response(ExportExecutionSerializer(queryset, many=True).data, status=status.HTTP_200_OK)

