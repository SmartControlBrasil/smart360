from rest_framework import serializers

from ..models import (
    ExportExecution,
    ExportProfile,
    ReportArtifact,
    ReportLog,
    ReportRequest,
    ReportTemplate,
    ScheduledReport,
)


class ReportTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportTemplate
        fields = (
            "id",
            "public_id",
            "name",
            "slug",
            "source_module",
            "report_type",
            "description",
            "output_format_default",
            "config_json",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class ReportRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportRequest
        fields = (
            "id",
            "public_id",
            "template",
            "requested_by",
            "requested_for_company",
            "source_module",
            "status",
            "output_format",
            "filters_json",
            "started_at",
            "completed_at",
            "failed_at",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "started_at", "completed_at", "failed_at", "error_message", "created_at", "updated_at")


class ReportArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportArtifact
        fields = (
            "id",
            "public_id",
            "report_request",
            "file",
            "artifact_type",
            "storage_path",
            "file_name",
            "mime_type",
            "size_bytes",
            "generated_at",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "generated_at", "created_at", "updated_at")


class ExportProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportProfile
        fields = (
            "id",
            "public_id",
            "name",
            "slug",
            "source_module",
            "export_type",
            "description",
            "columns_config",
            "filters_config",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class ExportExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportExecution
        fields = (
            "id",
            "public_id",
            "export_profile",
            "requested_by",
            "status",
            "output_format",
            "filters_json",
            "started_at",
            "completed_at",
            "failed_at",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "started_at", "completed_at", "failed_at", "error_message", "created_at", "updated_at")


class ReportLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportLog
        fields = ("id", "public_id", "source_module", "report_request", "export_execution", "log_level", "message", "payload", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class ScheduledReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledReport
        fields = (
            "id",
            "public_id",
            "name",
            "slug",
            "template",
            "owner_user",
            "owner_company",
            "schedule_type",
            "schedule_config",
            "output_format",
            "filters_json",
            "is_active",
            "last_run_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "slug", "last_run_at", "created_at", "updated_at")

