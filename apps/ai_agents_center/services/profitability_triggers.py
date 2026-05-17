from __future__ import annotations

from apps.ai_shared.interfaces.agent_coordinator import get_agent_coordinator
from apps.ai_agents_center.models import AgentRun
from apps.smart_system.models import MaintenanceClient, MaintenanceContract, OperationalSite, ServiceOrder, StockMovement


class ProfitabilityAgentTriggerService:
    @staticmethod
    def run_company_analysis(*, company, site=None, user=None, trigger_type=AgentRun.TriggerType.SCHEDULED, trigger_reference="scheduled:monthly"):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="profitability-agent",
            company=company,
            site=site,
            triggered_by=user,
            trigger_type=trigger_type,
            trigger_reference=trigger_reference,
        )

    @staticmethod
    def run_client_analysis(*, client: MaintenanceClient, user=None, trigger_type=AgentRun.TriggerType.MANUAL):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="profitability-agent",
            company=client.company,
            site=None,
            triggered_by=user,
            trigger_type=trigger_type,
            trigger_reference=f"client:{client.public_id}",
        )

    @staticmethod
    def run_contract_analysis(*, contract: MaintenanceContract, user=None, trigger_type=AgentRun.TriggerType.EVENT):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="profitability-agent",
            company=contract.company,
            site=contract.operational_site,
            triggered_by=user,
            trigger_type=trigger_type,
            trigger_reference=f"contract:{contract.public_id}",
        )

    @staticmethod
    def run_site_analysis(*, site: OperationalSite, user=None, trigger_type=AgentRun.TriggerType.EVENT):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="profitability-agent",
            company=site.maintenance_client.company,
            site=site,
            triggered_by=user,
            trigger_type=trigger_type,
            trigger_reference=f"site:{site.code}",
        )

    @staticmethod
    def run_technician_analysis(*, company, technician, target_date, site=None, user=None, trigger_type=AgentRun.TriggerType.EVENT):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="profitability-agent",
            company=company,
            site=site,
            triggered_by=user,
            trigger_type=trigger_type,
            trigger_reference=f"technician:{technician.id}:date:{target_date.isoformat()}",
        )

    @staticmethod
    def trigger_for_service_order(*, service_order: ServiceOrder, user=None):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="profitability-agent",
            company=service_order.client.company,
            site=service_order.operational_site,
            triggered_by=user,
            trigger_type=AgentRun.TriggerType.EVENT,
            trigger_reference=f"contract:{service_order.maintenance_contract.public_id}" if service_order.maintenance_contract_id else f"client:{service_order.client.public_id}",
        )

    @staticmethod
    def trigger_for_stock_movement(*, movement: StockMovement, user=None):
        if movement.service_order_id:
            return ProfitabilityAgentTriggerService.trigger_for_service_order(service_order=movement.service_order, user=user)
        if movement.operational_site_id:
            return ProfitabilityAgentTriggerService.run_site_analysis(site=movement.operational_site, user=user)
        return None
