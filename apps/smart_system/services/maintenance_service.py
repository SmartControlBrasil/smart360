from django.db import transaction
from django.utils import timezone

from apps.audit.services.audit_service import AuditService
from apps.ai_shared.interfaces.triggers import get_maintenance_agent_trigger_service, get_scheduling_agent_trigger_service

from ..models import AssetHistoryEvent, FailureEvent, ServiceOrder, WorkLog


class ServiceOrderNumberGenerator:
    @staticmethod
    def generate():
        date_prefix = timezone.now().strftime("%Y%m%d")
        latest_order = ServiceOrder.objects.filter(order_number__startswith=f"SS-{date_prefix}").order_by("-order_number").first()
        if not latest_order:
            sequence = 1
        else:
            sequence = int(latest_order.order_number.split("-")[-1]) + 1
        return f"SS-{date_prefix}-{sequence:04d}"


class AssetHistoryService:
    @staticmethod
    def create_event(*, asset, event_type, title, description="", related_service_order=None, related_failure_event=None, created_by=None):
        return AssetHistoryEvent.objects.create(
            asset=asset,
            event_type=event_type,
            title=title,
            description=description,
            related_service_order=related_service_order,
            related_failure_event=related_failure_event,
            created_by=created_by,
            occurred_at=timezone.now(),
        )


class ServiceOrderService:
    @staticmethod
    @transaction.atomic
    def create_service_order(*, user, validated_data):
        if not validated_data.get("order_number"):
            validated_data["order_number"] = ServiceOrderNumberGenerator.generate()
        service_order = ServiceOrder.objects.create(created_by=user, **validated_data)

        if service_order.asset:
            AssetHistoryService.create_event(
                asset=service_order.asset,
                event_type=AssetHistoryEvent.EventType.SERVICE_ORDER_CREATED,
                title=f"OS criada: {service_order.order_number}",
                description=service_order.title,
                related_service_order=service_order,
                created_by=user,
            )

        AuditService.log(
            action="smart_system.service_order.created",
            entity="service_order",
            entity_id=str(service_order.public_id),
            user=user,
            company=getattr(service_order.client, "company", None),
            payload={"order_number": service_order.order_number, "status": service_order.status},
        )
        if service_order.priority == ServiceOrder.Priority.URGENT:
            try:
                scheduling_trigger_service = get_scheduling_agent_trigger_service()
                scheduling_trigger_service.run_day_analysis(
                    company=service_order.client.company,
                    site=service_order.operational_site,
                    target_date=service_order.scheduled_start.date() if service_order.scheduled_start else timezone.localdate(),
                    trigger_type="event",
                    trigger_reference=f"date:{(service_order.scheduled_start.date() if service_order.scheduled_start else timezone.localdate()).isoformat()}",
                )
            except Exception:
                pass
        return service_order

    @staticmethod
    @transaction.atomic
    def update_service_order(*, service_order, validated_data, user):
        previous_status = service_order.status
        final_observations = validated_data.get("final_observations")
        for field, value in validated_data.items():
            setattr(service_order, field, value)

        if service_order.status == ServiceOrder.Status.IN_PROGRESS and not service_order.started_at:
            service_order.started_at = timezone.now()
        if service_order.status == ServiceOrder.Status.COMPLETED and not service_order.completed_at:
            service_order.completed_at = timezone.now()

        service_order.save()

        if service_order.asset and previous_status != service_order.status and service_order.status == ServiceOrder.Status.COMPLETED:
            AssetHistoryService.create_event(
                asset=service_order.asset,
                event_type=AssetHistoryEvent.EventType.SERVICE_ORDER_COMPLETED,
                title=f"OS concluida: {service_order.order_number}",
                description=final_observations or service_order.title,
                related_service_order=service_order,
                created_by=user,
            )

        AuditService.log(
            action="smart_system.service_order.updated",
            entity="service_order",
            entity_id=str(service_order.public_id),
            user=user,
            company=getattr(service_order.client, "company", None),
            payload={"status": service_order.status},
        )
        if previous_status != service_order.status and service_order.status in {ServiceOrder.Status.COMPLETED, ServiceOrder.Status.OPEN}:
            try:
                maintenance_trigger_service = get_maintenance_agent_trigger_service()
                maintenance_trigger_service.trigger_for_service_order(service_order=service_order, user=user)
            except Exception:
                pass
        return service_order


class FailureEventService:
    @staticmethod
    @transaction.atomic
    def create_failure_event(*, user, validated_data):
        failure_event = FailureEvent.objects.create(**validated_data)

        AssetHistoryService.create_event(
            asset=failure_event.asset,
            event_type=AssetHistoryEvent.EventType.FAILURE_REPORTED,
            title="Falha registrada",
            description=failure_event.symptom,
            related_service_order=failure_event.service_order,
            related_failure_event=failure_event,
            created_by=user,
        )

        AuditService.log(
            action="smart_system.failure_event.created",
            entity="failure_event",
            entity_id=str(failure_event.public_id),
            user=user,
            payload={"severity": failure_event.severity, "status": failure_event.status},
        )
        try:
            MaintenanceAgentTriggerService.trigger_for_failure_event(failure_event=failure_event, user=user)
        except Exception:
            pass
        return failure_event


class WorkLogService:
    @staticmethod
    def sync_labor_minutes(*, work_log):
        if work_log.started_at and work_log.ended_at:
            delta = work_log.ended_at - work_log.started_at
            work_log.labor_minutes = max(int(delta.total_seconds() // 60), 0)
        work_log.save()
        return work_log
