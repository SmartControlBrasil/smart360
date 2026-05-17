from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from apps.access_control_center.services.access_service import AccessAuditService
from apps.observability_center.services.observability_service import SystemEventService
from shared_kernel.observability.context import get_correlation_id, get_request_context, get_request_id

from ..models import ServiceOrder, ServiceSignature


@dataclass(frozen=True)
class SignatureCaptureResult:
    signature: ServiceSignature
    replaced_signature_id: str


class ServiceSignatureService:
    @staticmethod
    def get_service_order(order_code: str) -> ServiceOrder | None:
        return (
            ServiceOrder.objects.select_related(
                "client__company",
                "operational_site",
                "assigned_to",
            )
            .filter(order_number=order_code)
            .first()
        )

    @classmethod
    def capture_signature(
        cls,
        *,
        request,
        service_order: ServiceOrder,
        signature_type: str,
        signer_role: str,
        signer_name: str,
        signer_title: str = "",
        signer_document: str = "",
        signer_user=None,
        signature_data: str = "",
        acceptance_notes: str = "",
        missing_reason: str = "",
        missing_reason_notes: str = "",
        metadata: dict | None = None,
    ) -> SignatureCaptureResult:
        existing = (
            ServiceSignature.objects.filter(
                service_order=service_order,
                signature_type=signature_type,
                is_current=True,
            )
            .order_by("-version", "-created_at")
            .first()
        )
        next_version = (existing.version + 1) if existing else 1
        if existing:
            existing.is_current = False
            existing.save(update_fields=["is_current", "updated_at"])

        request_context = get_request_context()
        signature = ServiceSignature.objects.create(
            signature_type=signature_type,
            signer_role=signer_role,
            signer_name=signer_name,
            signer_title=signer_title,
            signer_document=signer_document,
            signer_user=signer_user,
            company=service_order.client.company,
            operational_site=service_order.operational_site,
            service_order=service_order,
            signed_at=timezone.now(),
            signature_data=signature_data,
            acceptance_notes=acceptance_notes,
            missing_reason=missing_reason,
            missing_reason_notes=missing_reason_notes,
            signed_ip=cls._get_request_ip(request),
            device_info=(request.META.get("HTTP_USER_AGENT", "") or "")[:255],
            request_id=get_request_id(),
            correlation_id=get_correlation_id(),
            version=next_version,
            metadata=metadata or {},
        )
        cls._log_signature_events(
            request=request,
            signature=signature,
            replaced_signature_id=str(existing.public_id) if existing else "",
            request_context=request_context,
        )
        return SignatureCaptureResult(
            signature=signature,
            replaced_signature_id=str(existing.public_id) if existing else "",
        )

    @classmethod
    def get_signature_summary(cls, service_order: ServiceOrder | None) -> dict:
        empty = {
            "technician_signature": None,
            "client_signature": None,
            "has_technician_signature": False,
            "has_client_signature": False,
            "has_client_resolution": False,
            "missing_reason_recorded": False,
        }
        if service_order is None:
            return empty
        signatures = list(service_order.service_signatures.filter(is_current=True).order_by("-signed_at"))
        technician = next(
            (
                item
                for item in signatures
                if item.signature_type == ServiceSignature.SignatureType.TECHNICIAN_COMPLETION
            ),
            None,
        )
        client = next(
            (
                item
                for item in signatures
                if item.signature_type == ServiceSignature.SignatureType.CLIENT_ACCEPTANCE
            ),
            None,
        )
        return {
            "technician_signature": technician,
            "client_signature": client,
            "has_technician_signature": technician is not None and bool(technician.signature_data),
            "has_client_signature": client is not None and bool(client.signature_data),
            "has_client_resolution": client is not None and (bool(client.signature_data) or bool(client.missing_reason)),
            "missing_reason_recorded": client is not None and bool(client.missing_reason),
        }

    @staticmethod
    def _get_request_ip(request) -> str:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    @classmethod
    def _log_signature_events(cls, *, request, signature: ServiceSignature, replaced_signature_id: str, request_context: dict):
        signature_kind = "client" if signature.signature_type == ServiceSignature.SignatureType.CLIENT_ACCEPTANCE else "technician"
        event_suffix = "missing_reason_recorded" if signature.missing_reason and not signature.signature_data else "captured"
        SystemEventService.log_system_event(
            event_type=f"signature.{signature_kind}.{event_suffix}",
            source_module="smart_system",
            message=f"Operational signature recorded for {signature.service_order.order_number}.",
            entity_type="service_signature",
            entity_id=str(signature.public_id),
            user=request.user,
            company=signature.company,
            site=signature.operational_site,
            request_id=signature.request_id,
            correlation_id=signature.correlation_id,
            request_path=request_context.get("path", ""),
            request_method=request_context.get("method", ""),
            payload={
                "signature_type": signature.signature_type,
                "signer_role": signature.signer_role,
                "service_order": signature.service_order.order_number,
                "has_signature_data": bool(signature.signature_data),
                "missing_reason": signature.missing_reason,
            },
        )
        AccessAuditService.log(
            user=request.user,
            action=f"{signature_kind}_signature_{event_suffix}",
            domain="service_signatures",
            decision="allow",
            reason="Operational service signature recorded.",
            resource_type="service_order",
            resource_id=signature.service_order.order_number,
            metadata={
                "signature_type": signature.signature_type,
                "signature_id": str(signature.public_id),
                "replaced_signature_id": replaced_signature_id,
                "missing_reason": signature.missing_reason,
            },
            company=signature.company,
            site=signature.operational_site,
            after_state={
                "signature_type": signature.signature_type,
                "signer_name": signature.signer_name,
                "signed_at": signature.signed_at.isoformat(),
                "missing_reason": signature.missing_reason,
                "version": signature.version,
            },
        )
