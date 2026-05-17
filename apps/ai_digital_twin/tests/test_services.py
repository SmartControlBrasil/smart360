from django.test import TestCase

from apps.ai_agents_center.models import AgentDefinition, AgentRecommendation, AgentRun
from apps.ai_digital_twin.models import DigitalTwin
from apps.ai_digital_twin.services.orchestrator import DigitalTwinOrchestrator
from apps.integration_bus.services.realtime_bus import RealtimeSubscriberRegistry
from apps.smart_system.models import FailureEvent
from tests.factories.core import UserFactory
from tests.factories.smart_system import (
    AssetFactory,
    FailureEventFactory,
    MaintenancePlanFactory,
    OperationalSiteFactory,
    ServiceOrderChecklistResponseFactory,
    ServiceOrderFactory,
)


class DigitalTwinServiceTests(TestCase):
    def setUp(self):
        self.user = UserFactory(is_staff=True)
        self.site = OperationalSiteFactory()
        self.company = self.site.maintenance_client.company
        self.asset = AssetFactory(operational_site=self.site, criticality="critical")
        self.order = ServiceOrderFactory(operational_site=self.site, asset=self.asset, client=self.site.maintenance_client, status="open", priority="urgent")
        self.failure = FailureEventFactory(asset=self.asset, service_order=self.order, severity=FailureEvent.Severity.CRITICAL)
        self.plan = MaintenancePlanFactory(asset=self.asset, operational_site=self.site, company=self.company)
        self.plan.next_due_date = self.plan.next_due_date.replace(day=max(1, self.plan.next_due_date.day - 1))
        self.plan.save(update_fields=["next_due_date", "updated_at"])
        self.agent = AgentDefinition.objects.create(
            name="Maintenance Intelligence Agent",
            slug="maintenance-agent",
            description="Agent",
            domain=AgentDefinition.Domain.MAINTENANCE,
            autonomy_level=1,
            status=AgentDefinition.Status.ACTIVE,
        )
        self.agent_run = AgentRun.objects.create(
            agent=self.agent,
            trigger_type=AgentRun.TriggerType.EVENT,
            trigger_reference=f"failure:{self.failure.public_id}",
            company=self.company,
            site=self.site,
            status=AgentRun.Status.COMPLETED,
            started_at=self.failure.detected_at,
            finished_at=self.failure.detected_at,
        )
        AgentRecommendation.objects.create(
            agent_run=self.agent_run,
            company=self.company,
            site=self.site,
            asset=self.asset,
            recommendation_type=AgentRecommendation.RecommendationType.ALERT,
            severity="high",
            title="Inspecionar ativo critico",
            summary="Falha critica recente exige revisao.",
            explanation="Contexto consolidado do agente.",
            status=AgentRecommendation.Status.OPEN,
        )

    def test_project_site_twin_persists_projection_and_snapshot(self):
        twin = DigitalTwinOrchestrator.project_for_site(site=self.site)
        self.assertEqual(twin.twin_type, DigitalTwin.TwinType.SITE_OPERATIONAL)
        self.assertIn(twin.risk_level, {"high", "critical"})
        self.assertTrue(twin.snapshots.exists())
        self.assertTrue(twin.projections.filter(projection_type="state").exists())
        self.assertTrue(twin.signals.filter(is_active=True).exists())

    def test_project_asset_twin_includes_checklist_nok_signal(self):
        ServiceOrderChecklistResponseFactory(
            service_order=self.order,
            response_boolean=False,
        )
        twin = DigitalTwinOrchestrator.project_for_asset(asset=self.asset)
        self.assertEqual(twin.twin_type, DigitalTwin.TwinType.ASSET_OPERATIONAL)
        self.assertGreaterEqual(twin.state_payload.get("recent_checklist_nok", 0), 1)
        self.assertTrue(twin.signals.filter(signal_type="checklist_nok", is_active=True).exists())

    def test_reactive_event_updates_site_and_asset_twins(self):
        twin_site = DigitalTwinOrchestrator.ensure_site_twin(site=self.site)
        twin_asset = DigitalTwinOrchestrator.ensure_asset_twin(asset=self.asset)
        event = self.company.integration_events.create(
            event_name="failures.created",
            event_version=1,
            source_module="smart_system",
            event_type="domain",
            site=self.site,
            aggregate_type="failure_event",
            aggregate_id=str(self.failure.public_id),
            payload={"asset_public_id": str(self.asset.public_id)},
            metadata={},
            request_id="req-digital-twin",
            priority="critical",
            status="published",
        )
        result = RealtimeSubscriberRegistry.twin_projection_refresh(event=event)
        twin_site.refresh_from_db()
        twin_asset.refresh_from_db()
        self.assertEqual(result.status, "delivered")
        self.assertIsNotNone(twin_site.last_projected_at)
        self.assertIsNotNone(twin_asset.last_projected_at)
