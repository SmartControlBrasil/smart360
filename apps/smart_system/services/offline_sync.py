from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.access_control_center.services.access_service import AccessAuditService
from apps.observability_center.services.observability_service import MetricCounterService, SystemEventService
from shared_kernel.observability.context import get_correlation_id, get_request_id

from ..models import FieldExecutionSnapshot, FieldSyncOperation, ServiceDocument, ServiceOrder, ServiceSignature
from .signature_service import ServiceSignatureService
from .tenant_scope import SmartSystemScopeService


ACTION_SEQUENCE = {
    "start_execution": 10,
    "save_execution": 20,
    "save_checklist": 30,
    "save_materials": 40,
    "upload_evidence": 50,
    "capture_signature": 60,
    "complete_execution": 70,
}


@dataclass(frozen=True)
class SyncOperationResult:
    operation_id: str
    status: str
    message: str
    snapshot_state: str = ""
    conflict_code: str = ""
    result_payload: dict | None = None


class OfflineSyncConflict(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class FieldOfflineSyncService:
    @classmethod
    def process_batch(cls, *, request, user, operations: list[dict]) -> dict:
        if not operations:
            return {"processed": [], "summary": {"processed": 0, "conflicts": 0, "errors": 0}}

        processed = []
        conflicts = 0
        errors = 0
        for index, operation in enumerate(sorted(operations, key=cls._sort_key)):
            try:
                result = cls.process_operation(request=request, user=user, operation=operation, index=index)
            except OfflineSyncConflict as exc:
                conflicts += 1
                operation_id = str(operation.get("operationId") or operation.get("client_operation_id") or "")
                processed.append(
                    {
                        "operation_id": operation_id,
                        "status": "conflict",
                        "message": exc.message,
                        "conflict_code": exc.code,
                    }
                )
                SystemEventService.log_system_event(
                    event_type="sync.conflict_detected",
                    source_module="technician_pwa",
                    severity="warning",
                    message="Offline sync conflict before operation persistence.",
                    entity_type="field_sync_operation",
                    entity_id=operation_id,
                    user=user,
                    company=None,
                    site=None,
                    request_id=get_request_id(),
                    correlation_id=get_correlation_id(),
                    payload={"action": operation.get("action"), "conflict_code": exc.code},
                )
            except Exception as exc:  # pragma: no cover - defensive path
                errors += 1
                operation_id = str(operation.get("operationId") or operation.get("client_operation_id") or "")
                processed.append(
                    {
                        "operation_id": operation_id,
                        "status": "error",
                        "message": str(exc),
                        "conflict_code": "",
                    }
                )
                SystemEventService.log_system_event(
                    event_type="sync.failed",
                    source_module="technician_pwa",
                    severity="error",
                    message="Unexpected field sync failure.",
                    entity_type="field_sync_operation",
                    entity_id=operation_id,
                    user=user,
                    company=None,
                    site=None,
                    request_id=get_request_id(),
                    correlation_id=get_correlation_id(),
                    payload={"error": str(exc), "action": operation.get("action")},
                )
            else:
                processed.append(
                    {
                        "operation_id": result.operation_id,
                        "status": result.status,
                        "message": result.message,
                        "snapshot_state": result.snapshot_state,
                        "conflict_code": result.conflict_code,
                        "result_payload": result.result_payload or {},
                    }
                )
                if result.status == FieldSyncOperation.Status.CONFLICT:
                    conflicts += 1
                elif result.status == FieldSyncOperation.Status.ERROR:
                    errors += 1

        return {
            "processed": processed,
            "summary": {
                "processed": len(processed) - conflicts - errors,
                "conflicts": conflicts,
                "errors": errors,
                "request_id": get_request_id(),
            },
        }

    @classmethod
    @transaction.atomic
    def process_operation(cls, *, request, user, operation: dict, index: int = 0) -> SyncOperationResult:
        action = (operation.get("action") or "").strip()
        operation_id = str(operation.get("operationId") or operation.get("client_operation_id") or "").strip()
        if not action or not operation_id:
            raise OfflineSyncConflict("invalid_payload", "A operação offline precisa informar action e operationId.")

        existing = FieldSyncOperation.objects.filter(client_operation_id=operation_id).select_related("service_order").first()
        if existing and existing.status in {FieldSyncOperation.Status.PROCESSED, FieldSyncOperation.Status.CONFLICT}:
            return SyncOperationResult(
                operation_id=operation_id,
                status=existing.status,
                message="Operação já processada anteriormente.",
                conflict_code=existing.error_code,
                result_payload=existing.result_payload,
            )

        order_code = operation.get("orderCode") or operation.get("order_code")
        if not order_code:
            raise OfflineSyncConflict("missing_order", "A operação offline precisa estar vinculada a uma ordem de serviço.")

        scoped_order = SmartSystemScopeService.scope_queryset(
            ServiceOrder.objects.select_related("client__company", "operational_site", "assigned_to"),
            request,
        ).filter(order_number=order_code).first()
        if scoped_order is None:
            raise OfflineSyncConflict("out_of_scope", "A ordem de serviço não pertence ao escopo ativo do técnico.")
        if scoped_order.assigned_to_id and scoped_order.assigned_to_id != user.id and not user.is_superuser:
            raise OfflineSyncConflict("assignment_mismatch", "A ordem de serviço não está atribuída ao técnico autenticado.")

        sync_operation = existing or FieldSyncOperation(
            client_operation_id=operation_id,
            company=scoped_order.client.company,
            operational_site=scoped_order.operational_site,
            service_order=scoped_order,
            technician=user,
        )
        sync_operation.action_type = action
        sync_operation.operation_order = operation.get("sequence") or ACTION_SEQUENCE.get(action, 999) + index
        sync_operation.payload = operation.get("payload") or {}
        sync_operation.status = FieldSyncOperation.Status.PENDING
        sync_operation.attempts = (sync_operation.attempts or 0) + 1
        sync_operation.request_id = get_request_id()
        sync_operation.correlation_id = get_correlation_id()
        sync_operation.metadata = {
            **(sync_operation.metadata or {}),
            "device_id": operation.get("deviceId", ""),
            "app_version": operation.get("appVersion", ""),
            "client_recorded_at": operation.get("recordedAt", ""),
        }
        sync_operation.save()

        snapshot, _ = FieldExecutionSnapshot.objects.get_or_create(
            service_order=scoped_order,
            technician=user,
            defaults={
                "company": scoped_order.client.company,
                "operational_site": scoped_order.operational_site,
                "execution_status": scoped_order.get_status_display(),
            },
        )

        try:
            result_payload = cls._dispatch_action(
                request=request,
                user=user,
                service_order=scoped_order,
                snapshot=snapshot,
                action=action,
                payload=sync_operation.payload,
                operation=sync_operation,
            )
        except OfflineSyncConflict as exc:
            snapshot.sync_state = FieldExecutionSnapshot.SyncState.CONFLICT
            snapshot.last_conflict_code = exc.code
            snapshot.last_conflict_message = exc.message
            snapshot.last_client_operation_id = operation_id
            snapshot.save(
                update_fields=[
                    "sync_state",
                    "last_conflict_code",
                    "last_conflict_message",
                    "last_client_operation_id",
                    "updated_at",
                ]
            )
            sync_operation.status = FieldSyncOperation.Status.CONFLICT
            sync_operation.error_code = exc.code
            sync_operation.error_message = exc.message
            sync_operation.processed_at = timezone.now()
            sync_operation.save(update_fields=["status", "error_code", "error_message", "processed_at", "updated_at"])
            SystemEventService.log_system_event(
                event_type="sync.conflict_detected",
                source_module="technician_pwa",
                severity="warning",
                message=f"Offline sync conflict for {service_order.order_number}.",
                entity_type="service_order",
                entity_id=service_order.order_number,
                user=user,
                company=service_order.client.company,
                site=service_order.operational_site,
                request_id=get_request_id(),
                correlation_id=get_correlation_id(),
                payload={"action": action, "conflict_code": exc.code},
            )
            return SyncOperationResult(
                operation_id=operation_id,
                status=FieldSyncOperation.Status.CONFLICT,
                message=exc.message,
                snapshot_state=snapshot.sync_state,
                conflict_code=exc.code,
            )

        snapshot.sync_state = FieldExecutionSnapshot.SyncState.SYNCED
        snapshot.last_conflict_code = ""
        snapshot.last_conflict_message = ""
        snapshot.last_server_sync_at = timezone.now()
        snapshot.last_client_operation_id = operation_id
        snapshot.local_device_id = operation.get("deviceId", "")
        snapshot.app_version = operation.get("appVersion", "")
        snapshot.save(
            update_fields=[
                "sync_state",
                "last_conflict_code",
                "last_conflict_message",
                "last_server_sync_at",
                "last_client_operation_id",
                "local_device_id",
                "app_version",
                "updated_at",
            ]
        )

        sync_operation.status = FieldSyncOperation.Status.PROCESSED
        sync_operation.result_payload = result_payload or {}
        sync_operation.error_code = ""
        sync_operation.error_message = ""
        sync_operation.processed_at = timezone.now()
        sync_operation.save(
            update_fields=[
                "status",
                "result_payload",
                "error_code",
                "error_message",
                "processed_at",
                "updated_at",
            ]
        )
        MetricCounterService.increment_metric(metric_key="offline_sync.processed", source_module="technician_pwa")
        SystemEventService.log_system_event(
            event_type="sync.succeeded",
            source_module="technician_pwa",
            message=f"Offline sync processed for {service_order.order_number}.",
            entity_type="field_sync_operation",
            entity_id=operation_id,
            user=user,
            company=service_order.client.company,
            site=service_order.operational_site,
            request_id=get_request_id(),
            correlation_id=get_correlation_id(),
            payload={"action": action, "order_code": service_order.order_number},
        )
        return SyncOperationResult(
            operation_id=operation_id,
            status=FieldSyncOperation.Status.PROCESSED,
            message="Operação sincronizada com sucesso.",
            snapshot_state=snapshot.sync_state,
            result_payload=result_payload,
        )

    @classmethod
    def get_snapshot_payload(cls, *, request, user, order_code: str) -> dict | None:
        service_order = SmartSystemScopeService.scope_queryset(
            ServiceOrder.objects.select_related("client__company", "operational_site", "assigned_to"),
            request,
        ).filter(order_number=order_code).first()
        if service_order is None:
            return None
        snapshot = (
            FieldExecutionSnapshot.objects.filter(service_order=service_order, technician=user)
            .order_by("-updated_at")
            .first()
        )
        if snapshot is None:
            return None
        return cls._serialize_snapshot(snapshot)

    @classmethod
    def _dispatch_action(cls, *, request, user, service_order, snapshot, action: str, payload: dict, operation: FieldSyncOperation) -> dict:
        if action == "start_execution":
            return cls._apply_start_execution(user=user, service_order=service_order, snapshot=snapshot, payload=payload)
        if action in {"save_execution", "save_checklist", "save_materials"}:
            return cls._apply_snapshot_update(user=user, service_order=service_order, snapshot=snapshot, action=action, payload=payload)
        if action == "upload_evidence":
            return cls._apply_evidence_upload(user=user, service_order=service_order, snapshot=snapshot, payload=payload, operation=operation)
        if action == "capture_signature":
            return cls._apply_signature_capture(request=request, user=user, service_order=service_order, snapshot=snapshot, payload=payload)
        if action == "complete_execution":
            return cls._apply_completion(user=user, service_order=service_order, snapshot=snapshot, payload=payload)
        raise OfflineSyncConflict("unsupported_action", f"Ação offline não suportada: {action}.")

    @classmethod
    def _assert_mutable_order(cls, service_order: ServiceOrder):
        if service_order.status in {ServiceOrder.Status.COMPLETED, ServiceOrder.Status.CANCELLED}:
            raise OfflineSyncConflict("order_closed", "A ordem de serviço já foi concluída ou cancelada no servidor.")

    @classmethod
    def _apply_start_execution(cls, *, user, service_order: ServiceOrder, snapshot: FieldExecutionSnapshot, payload: dict) -> dict:
        cls._assert_mutable_order(service_order)
        if not service_order.started_at:
            service_order.started_at = cls._parse_datetime(payload.get("startedAt")) or timezone.now()
        if not service_order.assigned_to_id:
            service_order.assigned_to = user
        service_order.status = ServiceOrder.Status.IN_PROGRESS
        service_order.save(update_fields=["started_at", "assigned_to", "status", "updated_at"])

        snapshot.execution_status = "Em execucao"
        snapshot.progress = max(snapshot.progress, int(payload.get("progress") or 5))
        snapshot.started_at = service_order.started_at
        snapshot.last_client_event_at = cls._parse_datetime(payload.get("recordedAt")) or timezone.now()
        snapshot.metadata = {**(snapshot.metadata or {}), "started_offline": True}
        snapshot.save(update_fields=["execution_status", "progress", "started_at", "last_client_event_at", "metadata", "updated_at"])

        AccessAuditService.log(
            user=user,
            action="offline_execution_started",
            domain="execution",
            decision="allow",
            resource_type="service_order",
            resource_id=service_order.order_number,
            reason="Offline technician execution synced.",
            company=service_order.client.company,
            site=service_order.operational_site,
            after_state={"status": service_order.status, "started_at": service_order.started_at.isoformat()},
        )
        return {"service_order_status": service_order.status, "started_at": service_order.started_at.isoformat()}

    @classmethod
    def _apply_snapshot_update(cls, *, user, service_order: ServiceOrder, snapshot: FieldExecutionSnapshot, action: str, payload: dict) -> dict:
        cls._assert_mutable_order(service_order)
        data = payload or {}
        snapshot.execution_status = data.get("executionStatus") or snapshot.execution_status or "Em execucao"
        snapshot.progress = min(max(int(data.get("progress") or snapshot.progress or 0), 0), 100)
        if data.get("checklist"):
            snapshot.checklist_payload = data["checklist"]
        if data.get("diagnosis"):
            snapshot.diagnosis_payload = data["diagnosis"]
        if data.get("executedAction"):
            snapshot.executed_action_payload = data["executedAction"]
        if data.get("materials"):
            snapshot.materials_payload = data["materials"]
        if data.get("evidence"):
            snapshot.evidence_payload = data["evidence"]
        if data.get("finalization"):
            snapshot.finalization_payload = data["finalization"]
        if data.get("hours"):
            snapshot.metadata = {**(snapshot.metadata or {}), "hours": data["hours"]}
        snapshot.last_client_event_at = cls._parse_datetime(data.get("recordedAt")) or timezone.now()
        snapshot.save(
            update_fields=[
                "execution_status",
                "progress",
                "checklist_payload",
                "diagnosis_payload",
                "executed_action_payload",
                "materials_payload",
                "evidence_payload",
                "finalization_payload",
                "last_client_event_at",
                "metadata",
                "updated_at",
            ]
        )
        event_name = "checklist.saved_offline" if action == "save_checklist" else "offline.payload.queued"
        SystemEventService.log_system_event(
            event_type=event_name,
            source_module="technician_pwa",
            message=f"Offline execution payload merged for {service_order.order_number}.",
            entity_type="service_order",
            entity_id=service_order.order_number,
            user=user,
            company=service_order.client.company,
            site=service_order.operational_site,
            request_id=get_request_id(),
            correlation_id=get_correlation_id(),
            payload={"action": action, "progress": snapshot.progress},
        )
        return {"progress": snapshot.progress, "sync_state": snapshot.sync_state}

    @classmethod
    def _apply_evidence_upload(cls, *, user, service_order: ServiceOrder, snapshot: FieldExecutionSnapshot, payload: dict, operation: FieldSyncOperation) -> dict:
        cls._assert_mutable_order(service_order)
        evidences = payload.get("evidences") or []
        created = []
        for index, evidence in enumerate(evidences):
            data_url = evidence.get("dataUrl") or ""
            if not data_url:
                continue
            content_file = cls._data_url_to_file(
                data_url,
                evidence.get("filename") or f"{service_order.order_number.lower()}-offline-{index}.png",
            )
            document = ServiceDocument.objects.create(
                service_order=service_order,
                file=content_file,
                document_type=cls._map_document_type(evidence.get("type")),
                title=evidence.get("description") or evidence.get("filename") or "Evidencia offline",
                uploaded_by=user,
            )
            created.append(
                {
                    "document_id": str(document.public_id),
                    "title": document.title,
                    "document_type": document.document_type,
                }
            )
        merged_evidence = list(snapshot.evidence_payload or [])
        merged_evidence.extend(payload.get("evidences") or [])
        snapshot.evidence_payload = merged_evidence
        snapshot.last_client_event_at = cls._parse_datetime(payload.get("recordedAt")) or timezone.now()
        snapshot.save(update_fields=["evidence_payload", "last_client_event_at", "updated_at"])
        return {"uploaded_documents": created, "operation_id": operation.client_operation_id}

    @classmethod
    def _apply_signature_capture(cls, *, request, user, service_order: ServiceOrder, snapshot: FieldExecutionSnapshot, payload: dict) -> dict:
        cls._assert_mutable_order(service_order)
        kind = payload.get("signatureKind")
        if kind == "technician":
            signature_type = ServiceSignature.SignatureType.TECHNICIAN_COMPLETION
            signer_role = ServiceSignature.SignerRole.TECHNICIAN
            signer_user = user
            signer_name = payload.get("signerName") or user.display_name or user.full_name or user.email
        else:
            signature_type = ServiceSignature.SignatureType.CLIENT_ACCEPTANCE
            signer_role = ServiceSignature.SignerRole.CLIENT_RESPONSIBLE
            signer_user = None
            signer_name = payload.get("signerName") or "Responsavel nao identificado"

        result = ServiceSignatureService.capture_signature(
            request=request,
            service_order=service_order,
            signature_type=signature_type,
            signer_role=signer_role,
            signer_name=signer_name,
            signer_title=payload.get("signerTitle", ""),
            signer_document=payload.get("signerDocument", ""),
            signer_user=signer_user,
            signature_data=payload.get("signatureData", ""),
            acceptance_notes=payload.get("acceptanceNotes", ""),
            missing_reason=payload.get("missingReason", ""),
            missing_reason_notes=payload.get("missingReasonNotes", ""),
            metadata={"origin": "offline_sync", "offline_operation": True},
        )
        event_name = "signature.technician.captured" if kind == "technician" else "signature.client.captured"
        SystemEventService.log_system_event(
            event_type=event_name,
            source_module="technician_pwa",
            message=f"Offline signature synchronized for {service_order.order_number}.",
            entity_type="service_signature",
            entity_id=str(result.signature.public_id),
            user=user,
            company=service_order.client.company,
            site=service_order.operational_site,
            request_id=get_request_id(),
            correlation_id=get_correlation_id(),
            payload={"signature_type": result.signature.signature_type, "missing_reason": result.signature.missing_reason},
        )
        return {"signature_id": str(result.signature.public_id), "signature_type": result.signature.signature_type}

    @classmethod
    def _apply_completion(cls, *, user, service_order: ServiceOrder, snapshot: FieldExecutionSnapshot, payload: dict) -> dict:
        cls._assert_mutable_order(service_order)
        summary = ServiceSignatureService.get_signature_summary(service_order)
        if not summary["has_technician_signature"]:
            raise OfflineSyncConflict("technician_signature_required", "A conclusão exige assinatura do técnico.")
        if not summary["has_client_resolution"]:
            raise OfflineSyncConflict("client_signature_required", "Registre a assinatura do cliente ou o motivo da ausência antes de concluir.")

        finalization = payload.get("finalization") or snapshot.finalization_payload or {}
        service_order.status = ServiceOrder.Status.COMPLETED
        service_order.completed_at = cls._parse_datetime(payload.get("completedAt")) or timezone.now()
        service_order.final_observations = finalization.get("finalNotes") or finalization.get("recommendation") or service_order.final_observations
        service_order.save(update_fields=["status", "completed_at", "final_observations", "updated_at"])

        snapshot.execution_status = "Concluida"
        snapshot.progress = 100
        snapshot.completed_at = service_order.completed_at
        snapshot.finalization_payload = finalization
        snapshot.last_client_event_at = cls._parse_datetime(payload.get("recordedAt")) or timezone.now()
        snapshot.save(
            update_fields=["execution_status", "progress", "completed_at", "finalization_payload", "last_client_event_at", "updated_at"]
        )
        AccessAuditService.log(
            user=user,
            action="offline_execution_completed",
            domain="execution",
            decision="allow",
            resource_type="service_order",
            resource_id=service_order.order_number,
            reason="Offline completion synchronized.",
            company=service_order.client.company,
            site=service_order.operational_site,
            after_state={
                "status": service_order.status,
                "completed_at": service_order.completed_at.isoformat(),
                "client_resolution": True,
            },
        )
        SystemEventService.log_system_event(
            event_type="work_order.closed_with_signatures",
            source_module="smart_system",
            message=f"Service order {service_order.order_number} closed after offline synchronization.",
            entity_type="service_order",
            entity_id=service_order.order_number,
            user=user,
            company=service_order.client.company,
            site=service_order.operational_site,
            request_id=get_request_id(),
            correlation_id=get_correlation_id(),
            payload={"offline": True},
        )
        return {"service_order_status": service_order.status, "completed_at": service_order.completed_at.isoformat()}

    @classmethod
    def _sort_key(cls, operation: dict):
        return (
            operation.get("sequence") or ACTION_SEQUENCE.get(operation.get("action"), 999),
            operation.get("recordedAt") or "",
        )

    @staticmethod
    def _parse_datetime(value):
        if not value:
            return None
        parsed = parse_datetime(value)
        if parsed is None:
            return None
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed

    @staticmethod
    def _map_document_type(value: str):
        normalized = (value or "").lower()
        if normalized in {"photo", "image", "foto"}:
            return ServiceDocument.DocumentType.PHOTO
        if normalized in {"report", "relatorio"}:
            return ServiceDocument.DocumentType.REPORT
        return ServiceDocument.DocumentType.OTHER

    @staticmethod
    def _data_url_to_file(data_url: str, filename: str) -> ContentFile:
        try:
            header, encoded = data_url.split(",", 1)
            _ = header
            binary = base64.b64decode(encoded)
        except (ValueError, binascii.Error) as exc:
            raise OfflineSyncConflict("invalid_evidence", "A evidência offline não pôde ser decodificada.") from exc
        return ContentFile(binary, name=filename)

    @staticmethod
    def _serialize_snapshot(snapshot: FieldExecutionSnapshot) -> dict:
        return {
            "snapshot_id": str(snapshot.public_id),
            "sync_state": snapshot.sync_state,
            "progress": snapshot.progress,
            "execution_status": snapshot.execution_status,
            "checklist": snapshot.checklist_payload,
            "diagnosis": snapshot.diagnosis_payload,
            "executed_action": snapshot.executed_action_payload,
            "materials": snapshot.materials_payload,
            "evidence": snapshot.evidence_payload,
            "finalization": snapshot.finalization_payload,
            "last_client_event_at": snapshot.last_client_event_at.isoformat() if snapshot.last_client_event_at else "",
            "last_server_sync_at": snapshot.last_server_sync_at.isoformat() if snapshot.last_server_sync_at else "",
            "last_conflict_code": snapshot.last_conflict_code,
            "last_conflict_message": snapshot.last_conflict_message,
        }
