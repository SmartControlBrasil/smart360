from __future__ import annotations


def get_anomaly_agent_trigger_service():
    from apps.ai_agents_center.services.anomaly_triggers import AnomalyAgentTriggerService

    return AnomalyAgentTriggerService


def get_maintenance_agent_trigger_service():
    from apps.ai_agents_center.services.maintenance_triggers import MaintenanceAgentTriggerService

    return MaintenanceAgentTriggerService


def get_marketplace_allocation_trigger_service():
    from apps.ai_agents_center.services.marketplace_triggers import MarketplaceAllocationTriggerService

    return MarketplaceAllocationTriggerService


def get_profitability_agent_trigger_service():
    from apps.ai_agents_center.services.profitability_triggers import ProfitabilityAgentTriggerService

    return ProfitabilityAgentTriggerService


def get_scheduling_agent_trigger_service():
    from apps.ai_agents_center.services.scheduling_triggers import SchedulingAgentTriggerService

    return SchedulingAgentTriggerService
