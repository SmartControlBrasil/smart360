from django.db import transaction
from django.utils import timezone

from apps.audit.services.audit_service import AuditService

from ..models import ProductionJob, ProductionStep, ShipmentPreparation


DEFAULT_PRODUCTION_STEPS = [
    ("Recebimento da arte", 1),
    ("Validacao tecnica", 2),
    ("Producao", 3),
    ("Embalagem", 4),
]


class ProductionQueueService:
    @staticmethod
    def next_queue_position():
        last_job = ProductionJob.objects.order_by("-queue_position").first()
        return (last_job.queue_position or 0) + 1 if last_job else 1


class ProductionJobService:
    @staticmethod
    @transaction.atomic
    def create_job(*, validated_data, user):
        if not validated_data.get("queue_position"):
            validated_data["queue_position"] = ProductionQueueService.next_queue_position()
        job = ProductionJob.objects.create(**validated_data)
        ProductionStep.objects.bulk_create(
            [
                ProductionStep(production_job=job, step_name=step_name, ordering=ordering)
                for step_name, ordering in DEFAULT_PRODUCTION_STEPS
            ]
        )
        order_item = job.order_item
        if order_item:
            order_item.status = order_item.Status.IN_PRODUCTION
            order_item.save(update_fields=["status", "updated_at"])
        if job.order:
            job.order.status = job.order.Status.IN_PRODUCTION
            job.order.save(update_fields=["status", "updated_at"])
        AuditService.log(
            action="caneca.production_job.created",
            entity="production_job",
            entity_id=str(job.public_id),
            user=user,
            payload={"job_type": job.job_type, "queue_position": job.queue_position},
        )
        return job

    @staticmethod
    def start_job(*, job):
        job.status = ProductionJob.Status.IN_PROGRESS
        if not job.started_at:
            job.started_at = timezone.now()
        job.save(update_fields=["status", "started_at", "updated_at"])
        return job

    @staticmethod
    def complete_job(*, job):
        job.status = ProductionJob.Status.COMPLETED
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "completed_at", "updated_at"])
        if job.order_item:
            job.order_item.status = job.order_item.Status.READY_TO_SHIP
            job.order_item.save(update_fields=["status", "updated_at"])
        if job.order:
            all_ready = not job.order.items.exclude(status=job.order.items.model.Status.READY_TO_SHIP).exists()
            if all_ready:
                job.order.status = job.order.Status.PAID
                job.order.save(update_fields=["status", "updated_at"])
        return job


class ShipmentService:
    @staticmethod
    def mark_posted(*, shipment):
        shipment.shipping_status = ShipmentPreparation.ShippingStatus.POSTED
        if not shipment.posted_at:
            shipment.posted_at = timezone.now()
        shipment.save(update_fields=["shipping_status", "posted_at", "updated_at"])
        shipment.order.status = shipment.order.Status.SHIPPED
        shipment.order.save(update_fields=["status", "updated_at"])
        return shipment
