from django.db import transaction
from django.utils import timezone

from apps.audit.services.audit_service import AuditService

from ..models import ProductionTask, SiteOrder, SiteOrderAnswer, Template
from .recommendation_service import RecommendationService
from .template_package import build_package_snapshot, final_price_should_use_template_default, resolve_package_price


DEFAULT_PRODUCTION_STAGES = [
    (ProductionTask.Stage.DISCOVERY, 1),
    (ProductionTask.Stage.COPYWRITING, 2),
    (ProductionTask.Stage.DESIGN, 3),
    (ProductionTask.Stage.DEVELOPMENT, 4),
    (ProductionTask.Stage.QA, 5),
    (ProductionTask.Stage.DELIVERY, 6),
]


class SiteOrderService:
    @staticmethod
    @transaction.atomic
    def create_order(*, requester, validated_data):
        answers_data = validated_data.pop("answers", [])
        selected_template = validated_data.get("selected_template")
        niche = validated_data["niche"]

        option_ids = [answer["option"].id for answer in answers_data if answer.get("option")]
        recommended_template = RecommendationService.recommend_template(niche=niche, option_ids=option_ids)
        if selected_template is None:
            validated_data["selected_template"] = recommended_template

        validated_data["recommended_template"] = recommended_template

        chosen_template = validated_data.get("selected_template") or recommended_template
        if chosen_template and final_price_should_use_template_default(validated_data.get("final_price")):
            price = resolve_package_price(chosen_template)
            if price is not None:
                validated_data["final_price"] = price

        md = dict(validated_data.get("metadata") or {})
        snapshot = build_package_snapshot(chosen_template)
        if snapshot:
            md["package_snapshot"] = snapshot
        validated_data["metadata"] = md

        order = SiteOrder.objects.create(requester=requester, **validated_data)

        SiteOrderService._create_answers(order=order, answers_data=answers_data)
        SiteOrderService._bootstrap_tasks(order=order)
        SiteOrderService._sync_production_dates(order=order)

        AuditService.log(
            action="site_factory.order.created",
            entity="site_order",
            entity_id=str(order.public_id),
            user=requester,
            company=order.company,
            payload={
                "niche": order.niche.slug,
                "selected_template": getattr(order.selected_template, "slug", None),
                "recommended_template": getattr(order.recommended_template, "slug", None),
                "status": order.status,
            },
        )
        return order

    @staticmethod
    def _create_answers(*, order, answers_data):
        answer_objects = [
            SiteOrderAnswer(
                site_order=order,
                question=answer["question"],
                option=answer.get("option"),
                value_text=answer.get("value_text", ""),
            )
            for answer in answers_data
        ]
        if answer_objects:
            SiteOrderAnswer.objects.bulk_create(answer_objects)

    @staticmethod
    def _bootstrap_tasks(*, order):
        tasks = [
            ProductionTask(site_order=order, stage=stage, order=sequence)
            for stage, sequence in DEFAULT_PRODUCTION_STAGES
        ]
        ProductionTask.objects.bulk_create(tasks)

    @staticmethod
    def _sync_production_dates(*, order):
        if order.status == SiteOrder.Status.IN_PRODUCTION and order.production_started_at is None:
            order.production_started_at = timezone.now()
            order.save(update_fields=["production_started_at", "updated_at"])
        if order.status == SiteOrder.Status.DELIVERED and order.delivered_at is None:
            order.delivered_at = timezone.now()
            order.save(update_fields=["delivered_at", "updated_at"])


class ProductionService:
    @staticmethod
    def mark_task_status(*, task, status):
        task.status = status
        task.save(update_fields=["status", "updated_at"])
        order = task.site_order
        if status == ProductionTask.Status.IN_PROGRESS and order.status == SiteOrder.Status.INTAKE_PENDING:
            order.status = SiteOrder.Status.IN_PRODUCTION
            order.production_started_at = timezone.now()
            order.save(update_fields=["status", "production_started_at", "updated_at"])
        return task


class DeliveryService:
    @staticmethod
    def register_delivery(*, record):
        order = record.site_order
        order.status = SiteOrder.Status.DELIVERED
        order.delivered_at = record.delivered_at
        order.save(update_fields=["status", "delivered_at", "updated_at"])

        AuditService.log(
            action="site_factory.order.delivered",
            entity="site_order",
            entity_id=str(order.public_id),
            user=order.requester,
            company=order.company,
            payload={"delivered_url": record.delivered_url, "acceptance_status": record.acceptance_status},
        )
        return record
