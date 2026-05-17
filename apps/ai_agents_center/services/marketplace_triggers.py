from __future__ import annotations

from apps.ai_shared.interfaces.agent_coordinator import get_agent_coordinator
from apps.ai_agents_center.models import AgentRun
from apps.marketplace_technicians.models import TechnicianAssignment, TechnicianServiceOffer, TechnicianServiceRequest


class MarketplaceAllocationTriggerService:
    @staticmethod
    def run_queue_analysis(*, company, site=None, user=None, trigger_type=AgentRun.TriggerType.SCHEDULED, trigger_reference="scheduled:marketplace-queue"):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="marketplace-agent",
            company=company,
            site=site,
            triggered_by=user,
            trigger_type=trigger_type,
            trigger_reference=trigger_reference,
        )

    @staticmethod
    def run_for_request(*, service_request: TechnicianServiceRequest, user=None, trigger_type=AgentRun.TriggerType.EVENT):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="marketplace-agent",
            company=service_request.requester_company,
            site=service_request.related_site,
            triggered_by=user,
            trigger_type=trigger_type,
            trigger_reference=f"request:{service_request.public_id}",
        )

    @staticmethod
    def run_for_offer(*, offer: TechnicianServiceOffer, user=None, trigger_type=AgentRun.TriggerType.EVENT):
        return MarketplaceAllocationTriggerService.run_for_request(service_request=offer.service_request, user=user, trigger_type=trigger_type)

    @staticmethod
    def run_for_assignment(*, assignment: TechnicianAssignment, user=None, trigger_type=AgentRun.TriggerType.EVENT):
        return MarketplaceAllocationTriggerService.run_for_request(service_request=assignment.technician_service_request, user=user, trigger_type=trigger_type)
