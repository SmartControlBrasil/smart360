from drf_spectacular.utils import extend_schema
from rest_framework import permissions, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from shared_kernel.api_docs.decorators import list_endpoint_schema
from shared_kernel.api_docs.responses import common_error_responses

from ..models import ErrorIncident, JobExecutionTrace, MetricCounter, RequestTrace, SystemEventLog
from ..services.observability_service import ObservabilitySummaryService
from .serializers import (
    ErrorIncidentSerializer,
    ErrorSummarySerializer,
    HealthSummarySerializer,
    JobExecutionTraceSerializer,
    MetricCounterSerializer,
    MetricsSummarySerializer,
    PlatformObservabilitySummarySerializer,
    RequestTraceSerializer,
    SystemEventLogSerializer,
)


class ObservabilityBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class SystemEventLogViewSet(ObservabilityBaseViewSet):
    queryset = SystemEventLog.objects.all()
    serializer_class = SystemEventLogSerializer
    filterset_fields = ("event_type", "source_module", "severity")
    search_fields = ("event_type", "source_module", "message", "correlation_id")
    ordering_fields = ("created_at", "updated_at")


class ErrorIncidentViewSet(ObservabilityBaseViewSet):
    queryset = ErrorIncident.objects.all()
    serializer_class = ErrorIncidentSerializer
    filterset_fields = ("source_module", "severity", "status", "error_type")
    search_fields = ("incident_key", "message", "notes")
    ordering_fields = ("last_seen_at", "created_at", "updated_at", "occurrences_count")


class MetricCounterViewSet(ObservabilityBaseViewSet):
    queryset = MetricCounter.objects.all()
    serializer_class = MetricCounterSerializer
    filterset_fields = ("metric_key", "source_module", "period_type", "reference_date")
    search_fields = ("metric_key", "source_module")
    ordering_fields = ("reference_date", "updated_at", "created_at", "value")


class JobExecutionTraceViewSet(ObservabilityBaseViewSet):
    queryset = JobExecutionTrace.objects.all()
    serializer_class = JobExecutionTraceSerializer
    filterset_fields = ("job_name", "source_module", "status")
    search_fields = ("job_name", "source_module", "correlation_id", "error_message")
    ordering_fields = ("started_at", "completed_at", "failed_at", "created_at")


class RequestTraceViewSet(ObservabilityBaseViewSet):
    queryset = RequestTrace.objects.select_related("user", "company", "site").all()
    serializer_class = RequestTraceSerializer
    filterset_fields = ("method", "status_code", "source_module", "company", "site")
    search_fields = ("request_id", "correlation_id", "path")
    ordering_fields = ("created_at", "duration_ms", "status_code")


class HealthSummaryView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Observability"],
        summary="Resumo de saude tecnica",
        description="Retorna o estado tecnico agregado da aplicacao, banco, cache e celery.",
        responses={200: HealthSummarySerializer},
    )
    def get(self, request, *args, **kwargs):
        return Response(ObservabilitySummaryService.health_summary())


class ErrorSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Observability"],
        summary="Resumo de incidentes",
        description="Consolida incidentes tecnicos por status e severidade.",
        responses={200: ErrorSummarySerializer, **common_error_responses()},
    )
    def get(self, request, *args, **kwargs):
        return Response(ObservabilitySummaryService.error_summary())


class MetricsSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Observability"],
        summary="Resumo de metricas tecnicas",
        description="Consolida counters tecnicos do dia corrente por modulo.",
        responses={200: MetricsSummarySerializer, **common_error_responses()},
    )
    def get(self, request, *args, **kwargs):
        return Response(ObservabilitySummaryService.metrics_summary())


class PlatformObservabilitySummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Observability"],
        summary="Resumo operacional da plataforma",
        description="Consolida saude, erros recentes, auditoria sensivel, jobs e riscos operacionais.",
        responses={200: PlatformObservabilitySummarySerializer, **common_error_responses()},
    )
    def get(self, request, *args, **kwargs):
        return Response(ObservabilitySummaryService.platform_summary())
