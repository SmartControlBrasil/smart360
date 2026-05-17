import json

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from ..models import ExportExecution, ReportArtifact, ReportLog, ReportRequest


class ReportLogService:
    @staticmethod
    def log(*, source_module, message, log_level=ReportLog.LogLevel.INFO, report_request=None, export_execution=None, payload=None):
        return ReportLog.objects.create(
            source_module=source_module,
            report_request=report_request,
            export_execution=export_execution,
            log_level=log_level,
            message=message,
            payload=payload or {},
        )


class ReportGenerationService:
    @staticmethod
    def _build_payload(*, source_module, config_json, filters_json):
        return {
            "source_module": source_module,
            "config": config_json or {},
            "filters": filters_json or {},
            "generated_at": timezone.now().isoformat(),
        }

    @staticmethod
    @transaction.atomic
    def run_report(*, report_request):
        report_request.status = ReportRequest.Status.RUNNING
        report_request.started_at = timezone.now()
        report_request.error_message = ""
        report_request.save(update_fields=["status", "started_at", "error_message", "updated_at"])

        payload = ReportGenerationService._build_payload(
            source_module=report_request.source_module,
            config_json=report_request.template.config_json,
            filters_json=report_request.filters_json,
        )
        content = json.dumps(payload, indent=2, ensure_ascii=True)
        file_name = f"{report_request.template.slug}-{report_request.public_id}.json"

        artifact = ReportArtifact.objects.create(
            report_request=report_request,
            artifact_type=ReportArtifact.ArtifactType.JSON,
            file_name=file_name,
            mime_type="application/json",
            size_bytes=len(content.encode("utf-8")),
            storage_path=f"reporting_center/{file_name}",
            metadata={"generated_from": "report_request"},
        )
        artifact.file.save(file_name, ContentFile(content.encode("utf-8")), save=True)

        report_request.status = ReportRequest.Status.COMPLETED
        report_request.completed_at = timezone.now()
        report_request.save(update_fields=["status", "completed_at", "updated_at"])

        ReportLogService.log(
            source_module=report_request.source_module,
            report_request=report_request,
            message=f"Report request {report_request.public_id} completed.",
            payload={"artifact_id": str(artifact.public_id)},
        )
        return report_request, artifact

    @staticmethod
    def fail_report(*, report_request, error_message):
        report_request.status = ReportRequest.Status.FAILED
        report_request.failed_at = timezone.now()
        report_request.error_message = error_message
        report_request.save(update_fields=["status", "failed_at", "error_message", "updated_at"])
        ReportLogService.log(
            source_module=report_request.source_module,
            report_request=report_request,
            log_level=ReportLog.LogLevel.ERROR,
            message=f"Report request {report_request.public_id} failed.",
            payload={"error_message": error_message},
        )
        return report_request


class ExportExecutionService:
    @staticmethod
    @transaction.atomic
    def run_export(*, export_execution):
        export_execution.status = ExportExecution.Status.RUNNING
        export_execution.started_at = timezone.now()
        export_execution.error_message = ""
        export_execution.save(update_fields=["status", "started_at", "error_message", "updated_at"])

        ReportLogService.log(
            source_module=export_execution.export_profile.source_module,
            export_execution=export_execution,
            message=f"Export execution {export_execution.public_id} completed.",
            payload={
                "columns": export_execution.export_profile.columns_config,
                "filters": export_execution.filters_json,
                "output_format": export_execution.output_format,
            },
        )

        export_execution.status = ExportExecution.Status.COMPLETED
        export_execution.completed_at = timezone.now()
        export_execution.save(update_fields=["status", "completed_at", "updated_at"])
        return export_execution

