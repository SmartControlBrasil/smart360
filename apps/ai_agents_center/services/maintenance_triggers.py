from __future__ import annotations

from apps.ai_shared.interfaces.agent_coordinator import get_agent_coordinator
from apps.ai_agents_center.models import AgentRun
from apps.smart_system.models import Asset, FailureEvent, MaintenancePlan, OperationalSite, ServiceOrder


class MaintenanceAgentTriggerService:
    @staticmethod
    def trigger_for_failure_event(*, failure_event: FailureEvent, user=None):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="maintenance-agent",
            company=failure_event.asset.operational_site.maintenance_client.company,
            site=failure_event.asset.operational_site,
            triggered_by=None,
            trigger_type=AgentRun.TriggerType.EVENT,
            trigger_reference=f"asset:{failure_event.asset.public_id}",
        )

    @staticmethod
    def trigger_for_service_order(*, service_order: ServiceOrder, user=None):
        if service_order.asset is None:
            return None
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="maintenance-agent",
            company=service_order.client.company,
            site=service_order.operational_site,
            triggered_by=None,
            trigger_type=AgentRun.TriggerType.EVENT,
            trigger_reference=f"asset:{service_order.asset.public_id}",
        )

    @staticmethod
    def trigger_for_preventive_plan(*, maintenance_plan: MaintenancePlan, user=None):
        asset = maintenance_plan.asset
        if asset is None:
            return None
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="maintenance-agent",
            company=maintenance_plan.company or asset.operational_site.maintenance_client.company,
            site=maintenance_plan.operational_site or asset.operational_site,
            triggered_by=None,
            trigger_type=AgentRun.TriggerType.EVENT,
            trigger_reference=f"asset:{asset.public_id}",
        )

    @staticmethod
    def run_site_analysis(*, site: OperationalSite, user=None, trigger_type=AgentRun.TriggerType.SCHEDULED, trigger_reference="scheduled:site"):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="maintenance-agent",
            company=site.maintenance_client.company,
            site=site,
            triggered_by=user,
            trigger_type=trigger_type,
            trigger_reference=trigger_reference,
        )

    @staticmethod
    def run_asset_analysis(*, asset: Asset, user=None, trigger_type=AgentRun.TriggerType.MANUAL):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="maintenance-agent",
            company=asset.operational_site.maintenance_client.company,
            site=asset.operational_site,
            triggered_by=user,
            trigger_type=trigger_type,
            trigger_reference=f"asset:{asset.public_id}",
        )
