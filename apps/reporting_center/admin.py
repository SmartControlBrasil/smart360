from django.contrib import admin

from .models import (
    ExportExecution,
    ExportProfile,
    ReportArtifact,
    ReportLog,
    ReportRequest,
    ReportTemplate,
    ScheduledReport,
)


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "source_module", "report_type", "output_format_default", "is_active")
    list_filter = ("source_module", "report_type", "output_format_default", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(ReportRequest)
class ReportRequestAdmin(admin.ModelAdmin):
    list_display = ("template", "source_module", "status", "output_format", "requested_by", "created_at")
    list_filter = ("source_module", "status", "output_format")
    search_fields = ("template__name", "error_message")
    readonly_fields = ("public_id", "started_at", "completed_at", "failed_at", "created_at", "updated_at")
    autocomplete_fields = ("template", "requested_by", "requested_for_company")


@admin.register(ReportArtifact)
class ReportArtifactAdmin(admin.ModelAdmin):
    list_display = ("report_request", "artifact_type", "file_name", "mime_type", "size_bytes", "generated_at")
    list_filter = ("artifact_type", "mime_type")
    search_fields = ("file_name", "storage_path")
    readonly_fields = ("public_id", "generated_at", "created_at", "updated_at")
    autocomplete_fields = ("report_request",)


@admin.register(ExportProfile)
class ExportProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "source_module", "export_type", "is_active", "created_by")
    list_filter = ("source_module", "export_type", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("created_by",)


@admin.register(ExportExecution)
class ExportExecutionAdmin(admin.ModelAdmin):
    list_display = ("export_profile", "status", "output_format", "requested_by", "created_at")
    list_filter = ("status", "output_format")
    search_fields = ("export_profile__name", "error_message")
    readonly_fields = ("public_id", "started_at", "completed_at", "failed_at", "created_at", "updated_at")
    autocomplete_fields = ("export_profile", "requested_by")


@admin.register(ReportLog)
class ReportLogAdmin(admin.ModelAdmin):
    list_display = ("source_module", "log_level", "report_request", "export_execution", "created_at")
    list_filter = ("source_module", "log_level")
    search_fields = ("message",)
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("report_request", "export_execution")


@admin.register(ScheduledReport)
class ScheduledReportAdmin(admin.ModelAdmin):
    list_display = ("name", "template", "schedule_type", "output_format", "is_active", "last_run_at")
    list_filter = ("schedule_type", "output_format", "is_active")
    search_fields = ("name", "slug")
    readonly_fields = ("public_id", "last_run_at", "created_at", "updated_at")
    autocomplete_fields = ("template", "owner_user", "owner_company")

