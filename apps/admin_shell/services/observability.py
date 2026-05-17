from apps.access_control_center.models import AccessAuditLog
from apps.observability_center.models import ErrorIncident, JobExecutionTrace, RequestTrace, SystemEventLog
from apps.observability_center.services.observability_service import ObservabilitySummaryService


def get_observability_dashboard_context():
    summary = ObservabilitySummaryService.platform_summary()
    health = summary["health"]

    health_widgets = [
        {
            "label": "Saude geral",
            "value": health.get("status", "unknown").upper(),
            "meta": f"{health.get('environment', 'unknown')} • {health.get('version', 'n/a')}",
            "tone": "emerald" if health.get("status") == "healthy" else "amber",
        },
        {
            "label": "Incidentes abertos",
            "value": str(ErrorIncident.objects.filter(status=ErrorIncident.Status.OPEN).count()),
            "meta": "incidentes tecnicos ainda sem resolucao",
            "tone": "red",
        },
        {
            "label": "Requests 5xx recentes",
            "value": str(RequestTrace.objects.filter(status_code__gte=500).count()),
            "meta": "rastro HTTP com erro para analise",
            "tone": "orange",
        },
        {
            "label": "Jobs em falha",
            "value": str(JobExecutionTrace.objects.filter(status=JobExecutionTrace.Status.FAILED).count()),
            "meta": "execucoes assicronas com erro registrado",
            "tone": "amber",
        },
    ]

    component_status = []
    for component, payload in health.get("checks", {}).items():
        component_status.append(
            {
                "name": component.replace("_", " ").title(),
                "status": payload.get("status", "unknown"),
                "details": payload.get("message")
                or payload.get("engine")
                or payload.get("backend")
                or payload.get("broker_url")
                or payload.get("result_backend")
                or "",
            }
        )

    return {
        "observability_health_widgets": health_widgets,
        "observability_component_status": component_status,
        "observability_recent_errors": summary["recent_errors"],
        "observability_critical_events": summary["critical_events"],
        "observability_audit_events": list(
            AccessAuditLog.objects.select_related("user", "company", "site").order_by("-created_at")[:8]
        ),
        "observability_request_traces": list(
            RequestTrace.objects.select_related("user", "company", "site").order_by("-created_at")[:10]
        ),
        "observability_job_traces": summary["recent_jobs"],
        "observability_billing_risk": summary["billing_risk"],
        "observability_event_totals": {
            "system_events": SystemEventLog.objects.count(),
            "audit_logs": AccessAuditLog.objects.count(),
            "request_traces": RequestTrace.objects.count(),
            "jobs": JobExecutionTrace.objects.count(),
        },
    }
