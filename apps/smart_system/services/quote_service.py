from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.access_control_center.services.access_service import AccessAuditService
from apps.ai_shared.interfaces.triggers import get_anomaly_agent_trigger_service, get_profitability_agent_trigger_service
from apps.observability_center.services.observability_service import SystemEventService

from ..models import Part, QuoteItem, ServiceOrder, ServiceQuote, StockMovement


class ServiceQuoteService:
    @staticmethod
    def _next_quote_number() -> str:
        sequence = ServiceQuote.objects.count() + 1
        return f"QTE-{timezone.localdate().year}-{sequence:04d}"

    @staticmethod
    def recalculate_totals(quote: ServiceQuote) -> ServiceQuote:
        items = list(quote.items.all())
        total_parts = Decimal("0")
        total_labor = Decimal("0")
        total_value = Decimal("0")
        for item in items:
            item.total_price = (item.quantity or Decimal("0")) * (item.unit_price or Decimal("0"))
            item.save(update_fields=["total_price", "updated_at"])
            total_value += item.total_price
            if item.item_type == QuoteItem.ItemType.PART:
                total_parts += item.total_price
            else:
                total_labor += item.total_price
        quote.total_parts = total_parts
        quote.total_labor = total_labor
        quote.total_value = total_value
        quote.save(update_fields=["total_parts", "total_labor", "total_value", "updated_at"])
        return quote

    @classmethod
    @transaction.atomic
    def create_quote(cls, *, user, validated_data: dict) -> ServiceQuote:
        items_data = validated_data.pop("items", [])
        work_order = validated_data["work_order"]
        company = validated_data.pop("company")
        operational_site = validated_data.pop("operational_site", None) or work_order.operational_site
        asset = validated_data.pop("asset", None) or work_order.asset
        quote = ServiceQuote.objects.create(
            quote_number=cls._next_quote_number(),
            company=company,
            operational_site=operational_site,
            asset=asset,
            created_by=user,
            updated_by=user,
            **validated_data,
        )
        for item_data in items_data:
            cls._create_item(quote=quote, item_data=item_data)
        cls.recalculate_totals(quote)
        cls._sync_work_order_quote_state(quote.work_order, quote)
        cls._log_event("quote.created", quote, user=user)
        return quote

    @classmethod
    def _create_item(cls, *, quote: ServiceQuote, item_data: dict) -> QuoteItem:
        stock_item = item_data.get("stock_item")
        part_reference = item_data.get("part_reference") or (stock_item.code if stock_item else "")
        available_quantity = stock_item.current_stock if stock_item else None
        if item_data.get("item_type") == QuoteItem.ItemType.LABOR and item_data.get("estimated_minutes") and item_data.get("hourly_rate"):
            hours = Decimal(item_data["estimated_minutes"]) / Decimal("60")
            item_data["quantity"] = hours.quantize(Decimal("0.01"))
            item_data["unit_price"] = item_data["hourly_rate"]
        return QuoteItem.objects.create(
            quote=quote,
            part_reference=part_reference,
            available_quantity=available_quantity,
            **item_data,
        )

    @classmethod
    @transaction.atomic
    def update_quote(cls, *, quote: ServiceQuote, user, validated_data: dict) -> ServiceQuote:
        items_data = validated_data.pop("items", None)
        for field, value in validated_data.items():
            setattr(quote, field, value)
        quote.updated_by = user
        quote.save()
        if items_data is not None:
            quote.items.all().delete()
            for item_data in items_data:
                cls._create_item(quote=quote, item_data=item_data)
        cls.recalculate_totals(quote)
        cls._sync_work_order_quote_state(quote.work_order, quote)
        cls._log_event("quote.updated", quote, user=user)
        return quote

    @classmethod
    @transaction.atomic
    def send_quote(cls, *, quote: ServiceQuote, user) -> ServiceQuote:
        quote.status = ServiceQuote.Status.SENT
        quote.sent_at = timezone.now()
        quote.updated_by = user
        quote.save(update_fields=["status", "sent_at", "updated_by", "updated_at"])
        cls._sync_work_order_quote_state(quote.work_order, quote)
        cls._log_event("quote.sent", quote, user=user)
        return quote

    @classmethod
    @transaction.atomic
    def approve_quote(cls, *, quote: ServiceQuote, approver_name: str, approver_user=None, notes: str = "") -> ServiceQuote:
        quote.status = ServiceQuote.Status.APPROVED
        quote.approved_at = timezone.now()
        quote.approved_by_name = approver_name
        quote.approved_by_user = approver_user
        quote.approval_notes = notes
        quote.save(
            update_fields=[
                "status",
                "approved_at",
                "approved_by_name",
                "approved_by_user",
                "approval_notes",
                "updated_at",
            ]
        )
        cls._reserve_parts(quote)
        cls._sync_work_order_quote_state(quote.work_order, quote)
        cls._log_event("quote.approved", quote, user=approver_user)
        try:
            profitability_trigger_service = get_profitability_agent_trigger_service()
            profitability_trigger_service.trigger_for_service_order(service_order=quote.work_order, user=approver_user)
        except Exception:
            pass
        try:
            anomaly_trigger_service = get_anomaly_agent_trigger_service()
            anomaly_trigger_service.trigger_for_service_order(service_order=quote.work_order, user=approver_user)
        except Exception:
            pass
        return quote

    @classmethod
    @transaction.atomic
    def reject_quote(cls, *, quote: ServiceQuote, approver_name: str, approver_user=None, reason: str = "") -> ServiceQuote:
        quote.status = ServiceQuote.Status.REJECTED
        quote.rejected_at = timezone.now()
        quote.approved_by_name = approver_name
        quote.approved_by_user = approver_user
        quote.rejection_reason = reason
        quote.save(
            update_fields=[
                "status",
                "rejected_at",
                "approved_by_name",
                "approved_by_user",
                "rejection_reason",
                "updated_at",
            ]
        )
        cls._sync_work_order_quote_state(quote.work_order, quote)
        cls._log_event("quote.rejected", quote, user=approver_user)
        try:
            profitability_trigger_service = get_profitability_agent_trigger_service()
            profitability_trigger_service.trigger_for_service_order(service_order=quote.work_order, user=approver_user)
        except Exception:
            pass
        try:
            anomaly_trigger_service = get_anomaly_agent_trigger_service()
            anomaly_trigger_service.trigger_for_service_order(service_order=quote.work_order, user=approver_user)
        except Exception:
            pass
        return quote

    @staticmethod
    def _reserve_parts(quote: ServiceQuote) -> None:
        for item in quote.items.filter(item_type=QuoteItem.ItemType.PART, stock_item__isnull=False):
            part = item.stock_item
            if part is None:
                continue
            part.current_stock = max(Decimal("0"), part.current_stock - item.quantity)
            part.save(update_fields=["current_stock", "updated_at"])
            StockMovement.objects.create(
                company=quote.company,
                operational_site=quote.operational_site,
                part=part,
                service_order=quote.work_order,
                movement_type=StockMovement.MovementType.RESERVED,
                quantity=item.quantity,
                reference_type="service_quote",
                reference_id=quote.quote_number,
                notes=f"Reserva automatica apos aprovacao do orcamento {quote.quote_number}.",
                performed_by=quote.approved_by_user or quote.updated_by or quote.created_by,
            )

    @staticmethod
    def _sync_work_order_quote_state(work_order: ServiceOrder, quote: ServiceQuote) -> None:
        work_order.quote_status = quote.status
        work_order.quote_required = quote.status in {
            ServiceQuote.Status.DRAFT,
            ServiceQuote.Status.SENT,
            ServiceQuote.Status.REJECTED,
        }
        work_order.quote_approved_at = quote.approved_at
        if quote.status == ServiceQuote.Status.SENT:
            work_order.status = ServiceOrder.Status.WAITING_QUOTE_APPROVAL
        elif quote.status == ServiceQuote.Status.APPROVED and work_order.status == ServiceOrder.Status.WAITING_QUOTE_APPROVAL:
            work_order.status = ServiceOrder.Status.SCHEDULED
        elif quote.status == ServiceQuote.Status.REJECTED:
            work_order.status = ServiceOrder.Status.ON_HOLD
        work_order.save(update_fields=["quote_status", "quote_required", "quote_approved_at", "status", "updated_at"])

    @staticmethod
    def _log_event(event_type: str, quote: ServiceQuote, user=None) -> None:
        SystemEventService.log_system_event(
            event_type=event_type,
            source_module="smart_system",
            message=f"Orcamento {quote.quote_number} atualizado.",
            entity_type="service_quote",
            entity_id=quote.quote_number,
            user=user,
            company=quote.company,
            site=quote.operational_site,
            payload={
                "quote_status": quote.status,
                "work_order": quote.work_order.order_number,
                "total_value": str(quote.total_value),
            },
        )
        AccessAuditService.log(
            user=user,
            action=event_type.replace(".", "_"),
            domain="quotes",
            decision="allow",
            resource_type="service_quote",
            resource_id=quote.quote_number,
            company=quote.company,
            site=quote.operational_site,
            metadata={"status": quote.status, "work_order": quote.work_order.order_number},
        )
