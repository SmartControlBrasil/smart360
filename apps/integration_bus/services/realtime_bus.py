from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from django.db import transaction
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.utils.text import slugify

from apps.ai_agents_center.services.anomaly_triggers import AnomalyAgentTriggerService
from apps.ai_agents_center.services.maintenance_triggers import MaintenanceAgentTriggerService
from apps.ai_agents_center.services.marketplace_triggers import MarketplaceAllocationTriggerService
from apps.ai_agents_center.services.profitability_triggers import ProfitabilityAgentTriggerService
from apps.ai_agents_center.services.scheduling_triggers import SchedulingAgentTriggerService
from apps.ai_digital_twin.services.orchestrator import DigitalTwinOrchestrator
from apps.ai_knowledge_graph.services.graph import GraphProjectionService
from apps.ai_policy_studio.models import PolicyRule
from apps.ai_policy_studio.services.engine import PolicyStudioEngine
from apps.marketplace_technicians.models import TechnicianServiceRequest
from apps.observability_center.models import SystemEventLog
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import FailureEvent, OperationalSite, Part
from shared_kernel.observability.context import get_correlation_id, get_request_id

from ..models import DeadLetterEvent, EventDelivery, EventSubscription, IntegrationEvent, ReactiveTriggerLog
from .event_catalog import event_priority_for, normalize_event_name
from .integration_service import IntegrationEventService


@dataclass(frozen=True)
class SubscriberResult:
    status: str
    summary: str
    payload: dict


class RealtimeSubscriberRegistry:
    @classmethod
    def get_handler(cls, handler_name: str):
        return {
            "realtime_update": cls.realtime_update,
            "briefing_refresh": cls.briefing_refresh,
            "copilot_context_refresh": cls.copilot_context_refresh,
            "reactive_agent_trigger": cls.reactive_agent_trigger,
            "twin_projection_refresh": cls.twin_projection_refresh,
            "knowledge_graph_projection_refresh": cls.knowledge_graph_projection_refresh,
        }.get(handler_name)

    @staticmethod
    def _policy_allows(*, event, action_type):
        result = PolicyStudioEngine.evaluate(
            module_slug="integration_bus",
            action_type=action_type,
            company=event.company,
            site=event.site,
            risk_level="high" if event.priority in {"high", "critical"} else "medium",
            autonomy_level=1,
            context={"event_name": event.event_name, "source_module": event.source_module},
        )
        return result

    @classmethod
    def realtime_update(cls, *, event: IntegrationEvent):
        policy = cls._policy_allows(event=event, action_type="event_to_dashboard_update")
        if not policy.allowed:
            SystemEventService.log_system_event(
                event_type="reactive_trigger.skipped",
                source_module="integration_bus",
                message=policy.reason,
                entity_type="integration_event",
                entity_id=str(event.public_id),
                company=event.company,
                site=event.site,
                payload={"target_component": "executive_war_room", "_skip_event_bus": True},
            )
            return SubscriberResult("skipped", policy.reason, {"policy_result": policy.result})
        trigger = ReactiveTriggerLog.objects.create(
            integration_event=event,
            target_component="executive_war_room",
            trigger_type=ReactiveTriggerLog.TriggerType.EVENT_TO_DASHBOARD_UPDATE,
            trigger_status=ReactiveTriggerLog.TriggerStatus.FIRED,
            summary=f"War room marcado para refresh pelo evento {event.event_name}.",
            payload={"event_name": event.event_name},
        )
        SystemEventService.log_system_event(
            event_type="ui.realtime.updated",
            source_module="integration_bus",
            message="War room realtime payload refreshed.",
            entity_type="integration_event",
            entity_id=str(event.public_id),
            company=event.company,
            site=event.site,
            payload={"target_component": "executive_war_room", "_skip_event_bus": True, "trigger_public_id": str(trigger.public_id)},
        )
        return SubscriberResult("delivered", trigger.summary, {"trigger_public_id": str(trigger.public_id)})

    @classmethod
    def briefing_refresh(cls, *, event: IntegrationEvent):
        policy = cls._policy_allows(event=event, action_type="event_to_briefing_refresh")
        status = ReactiveTriggerLog.TriggerStatus.FIRED if policy.allowed else ReactiveTriggerLog.TriggerStatus.SKIPPED
        summary = "Briefing marcado para refresh." if policy.allowed else policy.reason
        trigger = ReactiveTriggerLog.objects.create(
            integration_event=event,
            target_component="ai_briefings",
            trigger_type=ReactiveTriggerLog.TriggerType.EVENT_TO_BRIEFING_REFRESH,
            trigger_status=status,
            summary=summary,
            payload={"event_name": event.event_name},
        )
        return SubscriberResult("delivered" if policy.allowed else "skipped", summary, {"trigger_public_id": str(trigger.public_id)})

    @classmethod
    def copilot_context_refresh(cls, *, event: IntegrationEvent):
        policy = cls._policy_allows(event=event, action_type="event_to_copilot_refresh")
        status = ReactiveTriggerLog.TriggerStatus.FIRED if policy.allowed else ReactiveTriggerLog.TriggerStatus.SKIPPED
        summary = "Contexto do copilot marcado para refresh." if policy.allowed else policy.reason
        trigger = ReactiveTriggerLog.objects.create(
            integration_event=event,
            target_component="manager_copilot",
            trigger_type=ReactiveTriggerLog.TriggerType.EVENT_TO_COPILOT_REFRESH,
            trigger_status=status,
            summary=summary,
            payload={"event_name": event.event_name},
        )
        return SubscriberResult("delivered" if policy.allowed else "skipped", summary, {"trigger_public_id": str(trigger.public_id)})

    @classmethod
    def reactive_agent_trigger(cls, *, event: IntegrationEvent):
        policy = cls._policy_allows(event=event, action_type="event_to_agent_trigger")
        if not policy.allowed:
            SystemEventService.log_system_event(
                event_type="reactive_trigger.skipped",
                source_module="integration_bus",
                message=policy.reason,
                entity_type="integration_event",
                entity_id=str(event.public_id),
                company=event.company,
                site=event.site,
                payload={"target_component": "ai_agents_center", "_skip_event_bus": True},
            )
            trigger = ReactiveTriggerLog.objects.create(
                integration_event=event,
                target_component="ai_agents_center",
                trigger_type=ReactiveTriggerLog.TriggerType.EVENT_TO_AGENT_TRIGGER,
                trigger_status=ReactiveTriggerLog.TriggerStatus.SKIPPED,
                summary=policy.reason,
                payload={"event_name": event.event_name},
            )
            return SubscriberResult("skipped", policy.reason, {"trigger_public_id": str(trigger.public_id)})
        run = None
        if event.event_name == "failures.created":
            failure_event = FailureEvent.objects.select_related("asset", "asset__operational_site", "asset__operational_site__maintenance_client").get(public_id=event.aggregate_id)
            run = MaintenanceAgentTriggerService.trigger_for_failure_event(failure_event=failure_event)
        elif event.event_name == "work_orders.delayed":
            site = event.site or OperationalSite.objects.get(public_id=event.metadata.get("site_public_id"))
            company = event.company or site.maintenance_client.company
            run = SchedulingAgentTriggerService.run_day_analysis(
                company=company,
                site=site,
                target_date=timezone.localdate(),
                trigger_reference=f"event:{event.public_id}",
            )
        elif event.event_name == "billing.invoice_overdue":
            run = ProfitabilityAgentTriggerService.run_company_analysis(
                company=event.company,
                site=event.site,
                trigger_type="event",
                trigger_reference=f"event:{event.public_id}",
            )
        elif event.event_name == "marketplace.request_created":
            service_request = TechnicianServiceRequest.objects.select_related("requester_company", "related_site").get(public_id=event.aggregate_id)
            run = MarketplaceAllocationTriggerService.run_for_request(service_request=service_request)
        elif event.event_name == "inventory.low_stock_detected":
            part = Part.objects.select_related("company", "operational_site").get(public_id=event.aggregate_id)
            run = AnomalyAgentTriggerService.run_part_analysis(part=part)
        if run is None:
            raise ValueError(f"No reactive agent mapping for {event.event_name}.")
        trigger = ReactiveTriggerLog.objects.create(
            integration_event=event,
            target_component="ai_agents_center",
            trigger_type=ReactiveTriggerLog.TriggerType.EVENT_TO_AGENT_TRIGGER,
            trigger_status=ReactiveTriggerLog.TriggerStatus.FIRED,
            summary=f"Agent run disparado para {event.event_name}.",
            payload={"agent_run_public_id": str(run.public_id), "agent_slug": run.agent.slug},
        )
        SystemEventService.log_system_event(
            event_type="reactive_trigger.fired",
            source_module="integration_bus",
            message="Reactive AI trigger fired.",
            entity_type="integration_event",
            entity_id=str(event.public_id),
            company=event.company,
            site=event.site,
            payload={"target_component": "ai_agents_center", "_skip_event_bus": True, "agent_run_public_id": str(run.public_id)},
        )
        return SubscriberResult("delivered", trigger.summary, {"trigger_public_id": str(trigger.public_id)})

    @classmethod
    def twin_projection_refresh(cls, *, event: IntegrationEvent):
        twins = DigitalTwinOrchestrator.project_from_event(integration_event=event)
        trigger = ReactiveTriggerLog.objects.create(
            integration_event=event,
            target_component="ai_digital_twin",
            trigger_type=ReactiveTriggerLog.TriggerType.EVENT_TO_DASHBOARD_UPDATE,
            trigger_status=ReactiveTriggerLog.TriggerStatus.FIRED,
            summary=f"{len(twins)} twin(s) recalculados a partir de {event.event_name}.",
            payload={"twin_public_ids": [str(item.public_id) for item in twins]},
        )
        return SubscriberResult("delivered", trigger.summary, {"trigger_public_id": str(trigger.public_id), "twins": len(twins)})

    @classmethod
    def knowledge_graph_projection_refresh(cls, *, event: IntegrationEvent):
        run = GraphProjectionService.project_from_event(integration_event=event)
        summary = "Nenhuma projecao executada." if run is None else run.summary
        trigger = ReactiveTriggerLog.objects.create(
            integration_event=event,
            target_component="ai_knowledge_graph",
            trigger_type=ReactiveTriggerLog.TriggerType.EVENT_TO_DASHBOARD_UPDATE,
            trigger_status=ReactiveTriggerLog.TriggerStatus.FIRED,
            summary=summary,
            payload={"projection_run_public_id": str(run.public_id) if run else ""},
        )
        return SubscriberResult("delivered", summary, {"trigger_public_id": str(trigger.public_id), "projection_run": str(run.public_id) if run else ""})


class RealtimeEventBus:
    EVENT_STREAM_TYPES = {
        "decision.awaiting_approval",
        "agents.recommendation_created",
        "agents.anomaly_detected",
        "simulation.completed",
        "autonomy.execution_completed",
        "autonomy.execution_failed",
        "failures.created",
        "billing.invoice_overdue",
        "marketplace.request_created",
    }

    @classmethod
    def _matching_subscriptions(cls, event_name: str):
        subscriptions = EventSubscription.objects.filter(is_active=True)
        exact = subscriptions.filter(event_name=event_name)
        wildcard = [item for item in subscriptions.filter(event_name__endswith="*") if event_name.startswith(item.event_name[:-1])]
        return list(exact) + wildcard

    @classmethod
    @transaction.atomic
    def publish_domain_event(
        cls,
        *,
        event_name,
        source_module,
        aggregate_type="",
        aggregate_id="",
        payload=None,
        metadata=None,
        company=None,
        site=None,
        correlation_id="",
        request_id="",
        priority="",
        event_type=IntegrationEvent.EventType.DOMAIN,
    ):
        normalized_name = normalize_event_name(event_name)
        event_metadata = metadata or {}
        effective_request_id = request_id or get_request_id()
        effective_correlation_id = correlation_id or get_correlation_id()
        event_key_seed = event_metadata.get("system_event_public_id") or "|".join(
            [
                effective_correlation_id,
                effective_request_id,
                source_module,
                normalized_name,
                aggregate_type,
                str(aggregate_id),
            ]
        )
        event_key = slugify(event_key_seed)
        if len(event_key) > 180:
            digest = hashlib.sha256(event_key_seed.encode("utf-8")).hexdigest()[:32]
            event_key = f"{event_key[:147]}-{digest}"
        event = IntegrationEventService.record_event(
            event_name=normalized_name,
            event_version=1,
            event_key=event_key,
            source_module=source_module,
            event_type=event_type,
            company=company,
            site=site,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload or {},
            metadata=event_metadata,
            request_id=effective_request_id,
            correlation_id=effective_correlation_id,
            priority=priority or event_priority_for(normalized_name),
            occurred_at=timezone.now(),
        )
        if event.status == IntegrationEvent.Status.PUBLISHED and event.published_at:
            return event
        IntegrationEventService.publish_event(event=event)
        SystemEventService.log_system_event(
            event_type="event.published",
            source_module="integration_bus",
            message=f"Domain event {normalized_name} published.",
            entity_type=aggregate_type or "integration_event",
            entity_id=aggregate_id or str(event.public_id),
            company=company,
            site=site,
            payload={"event_public_id": str(event.public_id), "_skip_event_bus": True},
        )
        cls.route_event(event=event)
        return event

    @classmethod
    def publish_from_system_event(cls, *, system_event: SystemEventLog):
        if system_event.payload.get("_skip_event_bus"):
            return None
        if system_event.event_type.startswith("event.") or system_event.event_type.startswith("reactive_trigger.") or system_event.event_type.startswith("ui.realtime."):
            return None
        return cls.publish_domain_event(
            event_name=system_event.event_type,
            source_module=system_event.source_module,
            aggregate_type=system_event.entity_type,
            aggregate_id=system_event.entity_id,
            payload=system_event.payload,
            metadata={
                "system_event_public_id": str(system_event.public_id),
                "severity": system_event.severity,
                "request_path": system_event.request_path,
                "request_method": system_event.request_method,
            },
            company=system_event.company,
            site=system_event.site,
            correlation_id=system_event.correlation_id,
            request_id=system_event.request_id,
            priority=event_priority_for(system_event.event_type, fallback="normal"),
            event_type=IntegrationEvent.EventType.SYSTEM,
        )

    @classmethod
    def _deliver_to_subscription(cls, *, event: IntegrationEvent, subscription: EventSubscription):
        delivery, _ = EventDelivery.objects.get_or_create(
            integration_event=event,
            subscriber_name=f"{subscription.target_module}.{subscription.handler_name}",
            defaults={"subscription": subscription},
        )
        if delivery.delivery_status == EventDelivery.DeliveryStatus.DELIVERED:
            return delivery
        handler = RealtimeSubscriberRegistry.get_handler(subscription.handler_name)
        if handler is None:
            return cls._handle_delivery_failure(delivery=delivery, error_message=f"Unknown handler {subscription.handler_name}.")
        max_retries = int((subscription.retry_policy or {}).get("max_retries", 3))
        try:
            delivery.attempt_count += 1
            delivery.save(update_fields=["attempt_count", "updated_at"])
            result = handler(event=event)
            delivery.subscription = subscription
            delivery.delivery_status = {
                "delivered": EventDelivery.DeliveryStatus.DELIVERED,
                "skipped": EventDelivery.DeliveryStatus.SKIPPED,
            }.get(result.status, EventDelivery.DeliveryStatus.DELIVERED)
            delivery.last_error = ""
            delivery.delivery_payload = result.payload
            delivery.delivered_at = timezone.now()
            delivery.save(
                update_fields=["subscription", "attempt_count", "delivery_status", "last_error", "delivery_payload", "delivered_at", "updated_at"]
            )
            SystemEventService.log_system_event(
                event_type="event.delivered",
                source_module="integration_bus",
                message=f"Event {event.event_name} delivered to {delivery.subscriber_name}.",
                entity_type="integration_event",
                entity_id=str(event.public_id),
                company=event.company,
                site=event.site,
                payload={"subscriber": delivery.subscriber_name, "_skip_event_bus": True, "delivery_status": delivery.delivery_status},
            )
            return delivery
        except Exception as exc:
            if delivery.attempt_count + 1 >= max_retries:
                return cls._handle_delivery_failure(delivery=delivery, error_message=str(exc), dead_letter=True)
            delivery.attempt_count += 1
            delivery.delivery_status = EventDelivery.DeliveryStatus.RETRYING
            delivery.last_error = str(exc)
            delivery.save(update_fields=["attempt_count", "delivery_status", "last_error", "updated_at"])
            SystemEventService.log_system_event(
                event_type="event.retried",
                source_module="integration_bus",
                message=f"Retry agendado para {delivery.subscriber_name}.",
                entity_type="integration_event",
                entity_id=str(event.public_id),
                company=event.company,
                site=event.site,
                payload={"subscriber": delivery.subscriber_name, "_skip_event_bus": True, "attempt_count": delivery.attempt_count},
            )
            return cls._deliver_to_subscription(event=event, subscription=subscription)

    @classmethod
    def _handle_delivery_failure(cls, *, delivery: EventDelivery, error_message: str, dead_letter: bool = False):
        delivery.attempt_count = max(delivery.attempt_count, 1)
        delivery.delivery_status = EventDelivery.DeliveryStatus.DEAD_LETTER if dead_letter else EventDelivery.DeliveryStatus.FAILED
        delivery.last_error = error_message
        delivery.save(update_fields=["attempt_count", "delivery_status", "last_error", "updated_at"])
        if dead_letter:
            DeadLetterEvent.objects.create(
                original_event_name=delivery.integration_event.event_name,
                source_module=delivery.integration_event.source_module,
                payload={
                    **(delivery.integration_event.payload or {}),
                    "subscriber_name": delivery.subscriber_name,
                    "delivery_public_id": str(delivery.public_id),
                },
                failure_reason=error_message,
                retry_count=delivery.attempt_count,
            )
        SystemEventService.log_system_event(
            event_type="event.dlq_flagged" if dead_letter else "event.delivery_failed",
            source_module="integration_bus",
            message=f"Delivery failed for {delivery.subscriber_name}.",
            entity_type="integration_event",
            entity_id=str(delivery.integration_event.public_id),
            company=delivery.integration_event.company,
            site=delivery.integration_event.site,
            severity="error" if dead_letter else "warning",
            payload={"subscriber": delivery.subscriber_name, "_skip_event_bus": True, "error": error_message},
        )
        return delivery

    @classmethod
    def route_event(cls, *, event: IntegrationEvent):
        subscriptions = cls._matching_subscriptions(event.event_name)
        event.status = IntegrationEvent.Status.PROCESSING
        event.save(update_fields=["status", "updated_at"])
        for subscription in subscriptions:
            cls._deliver_to_subscription(event=event, subscription=subscription)
        if event.deliveries.filter(delivery_status__in=[EventDelivery.DeliveryStatus.FAILED, EventDelivery.DeliveryStatus.DEAD_LETTER]).exists():
            event.status = IntegrationEvent.Status.FAILED
        else:
            event.status = IntegrationEvent.Status.PROCESSED
            event.processed_at = timezone.now()
        event.save(update_fields=["status", "processed_at", "updated_at"])
        return event

    @classmethod
    def reprocess_delivery(cls, *, delivery: EventDelivery):
        if delivery.subscription is None:
            raise ValueError("Delivery sem subscription vinculada.")
        return cls._deliver_to_subscription(event=delivery.integration_event, subscription=delivery.subscription)

    @classmethod
    def event_chain(cls, *, event: IntegrationEvent):
        correlation_id = event.correlation_id
        if not correlation_id:
            return IntegrationEvent.objects.filter(pk=event.pk)
        return IntegrationEvent.objects.filter(correlation_id=correlation_id).order_by("occurred_at", "created_at")

    @classmethod
    def intelligence_feed(cls, *, company=None, site=None, limit=20):
        queryset = IntegrationEvent.objects.filter(event_name__in=cls.EVENT_STREAM_TYPES).order_by("-occurred_at", "-created_at")
        if company is not None:
            queryset = queryset.filter(company=company)
        if site is not None:
            queryset = queryset.filter(site=site)
        return list(queryset[:limit])

    @classmethod
    def sse_snapshot_response(cls, *, company=None, site=None, last_event_id=None):
        events = cls.intelligence_feed(company=company, site=site, limit=10)
        if last_event_id:
            events = [item for item in events if item.id > int(last_event_id)]
        decisions = IntegrationEvent.objects.filter(event_name="decision.awaiting_approval")
        if company is not None:
            decisions = decisions.filter(company=company)
        if site is not None:
            decisions = decisions.filter(site=site)
        pending_decisions_count = decisions.count()

        def iterator():
            payload = {
                "events": [
                    {
                        "public_id": str(item.public_id),
                        "event_name": item.event_name,
                        "priority": item.priority,
                        "summary": item.payload.get("summary") or item.metadata.get("severity") or item.event_name,
                        "occurred_at": item.occurred_at.isoformat(),
                    }
                    for item in events
                ],
                "pending_decisions_count": pending_decisions_count,
                "generated_at": timezone.now().isoformat(),
            }
            yield f"id: {events[0].id if events else 0}\n".encode("utf-8")
            yield b"event: war_room.snapshot\n"
            yield f"data: {json.dumps(payload)}\n\n".encode("utf-8")

        return StreamingHttpResponse(iterator(), content_type="text/event-stream")
