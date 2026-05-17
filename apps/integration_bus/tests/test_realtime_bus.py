from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.ai_agents_center.models import AgentRun
from apps.integration_bus.models import DeadLetterEvent, EventDelivery, EventSubscription, IntegrationEvent, ReactiveTriggerLog
from apps.integration_bus.services.realtime_bus import RealtimeEventBus
from apps.observability_center.models import SystemEventLog
from tests.factories.core import MembershipFactory
from tests.factories.smart_system import AssetFactory, FailureEventFactory, OperationalSiteFactory


class RealtimeEventBusServiceTests(TestCase):
    def setUp(self):
        self.membership = MembershipFactory()
        self.company = self.membership.company
        self.user = self.membership.user
        self.site = OperationalSiteFactory(maintenance_client__company=self.company)
        self.asset = AssetFactory(operational_site=self.site)

    def test_publish_domain_event_creates_envelope_and_deliveries(self):
        event = RealtimeEventBus.publish_domain_event(
            event_name="decision.awaiting_approval",
            source_module="ai_decision_engine",
            company=self.company,
            site=self.site,
            aggregate_type="decision",
            aggregate_id="decision-001",
            payload={"summary": "Approval required"},
            metadata={"origin": "test"},
            correlation_id="corr-event-001",
            request_id="req-event-001",
        )

        self.assertEqual(event.event_name, "decision.awaiting_approval")
        self.assertEqual(event.company, self.company)
        self.assertEqual(event.site, self.site)
        self.assertEqual(event.request_id, "req-event-001")
        self.assertTrue(event.deliveries.filter(subscriber_name="executive_war_room.realtime_update").exists())
        self.assertTrue(ReactiveTriggerLog.objects.filter(integration_event=event, target_component="executive_war_room").exists())
        self.assertTrue(SystemEventLog.objects.filter(event_type="event.published").exists())
        self.assertTrue(SystemEventLog.objects.filter(event_type="event.delivered").exists())

    @patch("apps.integration_bus.services.realtime_bus.MaintenanceAgentTriggerService.trigger_for_failure_event")
    def test_reactive_failure_event_triggers_agent_once_and_is_idempotent(self, trigger_for_failure_event):
        failure_event = FailureEventFactory(asset=self.asset)
        trigger_for_failure_event.return_value = type(
            "RunStub",
            (),
            {"public_id": failure_event.public_id, "agent": type("AgentStub", (), {"slug": "maintenance-agent"})()},
        )()
        event = RealtimeEventBus.publish_domain_event(
            event_name="failures.created",
            source_module="smart_system",
            company=self.company,
            site=self.site,
            aggregate_type="failure_event",
            aggregate_id=str(failure_event.public_id),
            payload={"severity": "critical"},
        )

        delivery = event.deliveries.get(subscriber_name="ai_agents_center.reactive_agent_trigger")
        RealtimeEventBus.reprocess_delivery(delivery=delivery)

        self.assertEqual(trigger_for_failure_event.call_count, 1)
        self.assertEqual(delivery.delivery_status, EventDelivery.DeliveryStatus.DELIVERED)
        self.assertTrue(ReactiveTriggerLog.objects.filter(integration_event=event, trigger_type="event_to_agent_trigger").exists())

    def test_failed_delivery_moves_to_dead_letter(self):
        EventSubscription.objects.create(
            event_name="decision.awaiting_approval",
            target_module="broken_module",
            handler_name="unknown_handler",
            is_active=True,
            execution_mode=EventSubscription.ExecutionMode.ASYNC,
            retry_policy={"max_retries": 1},
        )

        event = RealtimeEventBus.publish_domain_event(
            event_name="decision.awaiting_approval",
            source_module="ai_decision_engine",
            company=self.company,
            site=self.site,
            aggregate_type="decision",
            aggregate_id="decision-dead-letter",
            payload={"summary": "Broken subscriber"},
        )

        delivery = event.deliveries.get(subscriber_name="broken_module.unknown_handler")
        self.assertEqual(delivery.delivery_status, EventDelivery.DeliveryStatus.DEAD_LETTER)
        self.assertTrue(DeadLetterEvent.objects.filter(original_event_name="decision.awaiting_approval").exists())
        self.assertTrue(SystemEventLog.objects.filter(event_type="event.dlq_flagged").exists())


class RealtimeEventBusApiTests(APITestCase):
    def setUp(self):
        self.membership = MembershipFactory()
        self.company = self.membership.company
        self.user = self.membership.user
        self.site = OperationalSiteFactory(maintenance_client__company=self.company)
        self.client.force_authenticate(self.user)

    def test_feed_chain_and_delivery_endpoints_respect_company_scope(self):
        visible = RealtimeEventBus.publish_domain_event(
            event_name="decision.awaiting_approval",
            source_module="ai_decision_engine",
            company=self.company,
            site=self.site,
            aggregate_type="decision",
            aggregate_id="decision-visible",
            correlation_id="corr-visible",
        )
        other_membership = MembershipFactory()
        hidden_site = OperationalSiteFactory(maintenance_client__company=other_membership.company)
        RealtimeEventBus.publish_domain_event(
            event_name="decision.awaiting_approval",
            source_module="ai_decision_engine",
            company=other_membership.company,
            site=hidden_site,
            aggregate_type="decision",
            aggregate_id="decision-hidden",
            correlation_id="corr-hidden",
        )

        feed_response = self.client.get(reverse("integration-events-intelligence-feed"))
        chain_response = self.client.get(reverse("integration-events-chain", args=[visible.id]))
        deliveries_response = self.client.get(reverse("integration-deliveries-list"))

        self.assertEqual(feed_response.status_code, status.HTTP_200_OK)
        self.assertEqual(chain_response.status_code, status.HTTP_200_OK)
        self.assertEqual(deliveries_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(feed_response.data), 1)
        self.assertEqual(chain_response.data[0]["aggregate_id"], "decision-visible")
        self.assertTrue(all(item["integration_event"] == visible.id for item in deliveries_response.data["results"]))
