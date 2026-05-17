from __future__ import annotations

from apps.ai_shared.interfaces.agent_coordinator import get_agent_coordinator
from apps.ai_agents_center.models import AgentRun
from apps.marketplace_technicians.models import TechnicianAssignment, TechnicianServiceRequest
from apps.smart_system.models import Asset, FailureEvent, MaintenanceClient, MaintenanceContract, OperationalSite, Part, ServiceOrder, StockMovement


class AnomalyAgentTriggerService:
    @staticmethod
    def run_company_analysis(*, company, site=None, user=None, trigger_type=AgentRun.TriggerType.SCHEDULED, trigger_reference="scheduled:daily-operations"):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="anomaly-agent",
            company=company,
            site=site,
            triggered_by=user,
            trigger_type=trigger_type,
            trigger_reference=trigger_reference,
        )

    @staticmethod
    def run_asset_analysis(*, asset: Asset, user=None, trigger_type=AgentRun.TriggerType.EVENT):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="anomaly-agent",
            company=asset.operational_site.maintenance_client.company,
            site=asset.operational_site,
            triggered_by=user,
            trigger_type=trigger_type,
            trigger_reference=f"asset:{asset.public_id}",
        )

    @staticmethod
    def run_site_analysis(*, site: OperationalSite, user=None, trigger_type=AgentRun.TriggerType.EVENT):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="anomaly-agent",
            company=site.maintenance_client.company,
            site=site,
            triggered_by=user,
            trigger_type=trigger_type,
            trigger_reference=f"site:{site.code}",
        )

    @staticmethod
    def run_client_analysis(*, client: MaintenanceClient, user=None, trigger_type=AgentRun.TriggerType.EVENT):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="anomaly-agent",
            company=client.company,
            triggered_by=user,
            trigger_type=trigger_type,
            trigger_reference=f"client:{client.public_id}",
        )

    @staticmethod
    def run_contract_analysis(*, contract: MaintenanceContract, user=None, trigger_type=AgentRun.TriggerType.EVENT):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="anomaly-agent",
            company=contract.company,
            site=contract.operational_site,
            triggered_by=user,
            trigger_type=trigger_type,
            trigger_reference=f"contract:{contract.public_id}",
        )

    @staticmethod
    def run_part_analysis(*, part: Part, user=None, trigger_type=AgentRun.TriggerType.EVENT):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="anomaly-agent",
            company=part.company,
            site=part.operational_site,
            triggered_by=user,
            trigger_type=trigger_type,
            trigger_reference=f"part:{part.public_id}",
        )

    @staticmethod
    def trigger_for_service_order(*, service_order: ServiceOrder, user=None):
        if service_order.asset_id:
            return AnomalyAgentTriggerService.run_asset_analysis(asset=service_order.asset, user=user)
        return AnomalyAgentTriggerService.run_site_analysis(site=service_order.operational_site, user=user)

    @staticmethod
    def trigger_for_failure(*, failure_event: FailureEvent, user=None):
        return AnomalyAgentTriggerService.run_asset_analysis(asset=failure_event.asset, user=user)

    @staticmethod
    def trigger_for_stock_movement(*, movement: StockMovement, user=None):
        if movement.part_id:
            return AnomalyAgentTriggerService.run_part_analysis(part=movement.part, user=user)
        if movement.operational_site_id:
            return AnomalyAgentTriggerService.run_site_analysis(site=movement.operational_site, user=user)
        return None

    @staticmethod
    def trigger_for_marketplace_request(*, service_request: TechnicianServiceRequest, user=None):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="anomaly-agent",
            company=service_request.requester_company,
            site=service_request.related_site,
            triggered_by=user,
            trigger_type=AgentRun.TriggerType.EVENT,
            trigger_reference=f"site:{service_request.related_site.code}" if service_request.related_site_id else "scheduled:marketplace-queue",
        )

    @staticmethod
    def trigger_for_marketplace_assignment(*, assignment: TechnicianAssignment, user=None):
        return AnomalyAgentTriggerService.trigger_for_marketplace_request(
            service_request=assignment.technician_service_request,
            user=user,
        )
