from django.contrib import admin

from .models import ErrorIncident, JobExecutionTrace, MetricCounter, RequestTrace, SystemEventLog


@admin.register(SystemEventLog)
class SystemEventLogAdmin(admin.ModelAdmin):
    list_display = (
        "event_type",
        "source_module",
        "severity",
        "user",
        "company",
        "site",
        "request_id",
        "created_at",
    )
    list_filter = ("source_module", "severity", "event_type", "company", "site", "created_at")
    search_fields = ("event_type", "message", "correlation_id", "request_id", "entity_type", "entity_id")
    readonly_fields = ("public_id", "created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(ErrorIncident)
class ErrorIncidentAdmin(admin.ModelAdmin):
    list_display = (
        "incident_key",
        "source_module",
        "error_type",
        "severity",
        "status",
        "company",
        "site",
        "occurrences_count",
        "last_seen_at",
    )
    list_filter = ("source_module", "severity", "status", "error_type", "company", "site")
    search_fields = ("incident_key", "message", "notes", "request_id", "correlation_id", "request_path")
    readonly_fields = ("public_id", "first_seen_at", "last_seen_at", "occurrences_count", "created_at", "updated_at")
    ordering = ("-last_seen_at",)


@admin.register(MetricCounter)
class MetricCounterAdmin(admin.ModelAdmin):
    list_display = ("metric_key", "source_module", "value", "period_type", "reference_date", "updated_at")
    list_filter = ("source_module", "period_type", "reference_date")
    search_fields = ("metric_key",)
    readonly_fields = ("public_id", "created_at", "updated_at")
    ordering = ("-reference_date", "metric_key")


@admin.register(JobExecutionTrace)
class JobExecutionTraceAdmin(admin.ModelAdmin):
    list_display = (
        "job_name",
        "source_module",
        "status",
        "user",
        "company",
        "site",
        "request_id",
        "started_at",
        "completed_at",
        "failed_at",
    )
    list_filter = ("source_module", "status", "company", "site", "started_at")
    search_fields = ("job_name", "correlation_id", "request_id", "error_message")
    readonly_fields = ("public_id", "duration_ms", "created_at", "updated_at")
    ordering = ("-started_at",)


@admin.register(RequestTrace)
class RequestTraceAdmin(admin.ModelAdmin):
    list_display = (
        "request_id",
        "method",
        "path",
        "status_code",
        "duration_ms",
        "company",
        "site",
        "created_at",
    )
    list_filter = ("method", "status_code", "source_module", "company", "site", "created_at")
    search_fields = ("request_id", "correlation_id", "path", "ip_address")
    readonly_fields = ("public_id", "created_at")
    ordering = ("-created_at",)
