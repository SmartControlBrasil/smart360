from __future__ import annotations

from apps.ai_shared.interfaces.agent_coordinator import get_agent_coordinator
from apps.ai_agents_center.models import AgentRun
from apps.smart_system.models import OperationalSite, ScheduledVisit


class SchedulingAgentTriggerService:
    @staticmethod
    def run_day_analysis(*, company, site=None, target_date, trigger_type=AgentRun.TriggerType.SCHEDULED, trigger_reference=""):
        trigger_reference = trigger_reference or (f"site:{site.code}:date:{target_date.isoformat()}" if site else f"date:{target_date.isoformat()}")
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="scheduling-agent",
            company=company,
            site=site,
            triggered_by=None,
            trigger_type=trigger_type,
            trigger_reference=trigger_reference,
        )

    @staticmethod
    def run_technician_analysis(*, company, technician, target_date, site=None, trigger_type=AgentRun.TriggerType.EVENT):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="scheduling-agent",
            company=company,
            site=site,
            triggered_by=None,
            trigger_type=trigger_type,
            trigger_reference=f"technician:{technician.id}:date:{target_date.isoformat()}",
        )

    @staticmethod
    def run_for_visit(*, visit: ScheduledVisit, trigger_type=AgentRun.TriggerType.EVENT):
        coordinator_service = get_agent_coordinator()
        return coordinator_service.run_agent(
            agent_slug="scheduling-agent",
            company=visit.company,
            site=visit.operational_site,
            triggered_by=None,
            trigger_type=trigger_type,
            trigger_reference=f"date:{visit.scheduled_date.isoformat()}",
        )

    @staticmethod
    def run_for_site(*, site: OperationalSite, target_date, trigger_type=AgentRun.TriggerType.SCHEDULED):
        return SchedulingAgentTriggerService.run_day_analysis(
            company=site.maintenance_client.company,
            site=site,
            target_date=target_date,
            trigger_type=trigger_type,
        )
