from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.ai_agents_center.models import AgentRun
from apps.ai_agents_center.services.maintenance_triggers import MaintenanceAgentTriggerService
from apps.ai_agents_center.services.registry import AgentRegistryService
from apps.ai_agents_center.services.scheduling_triggers import SchedulingAgentTriggerService
from apps.smart_system.models import OperationalSite


@dataclass(frozen=True)
class OperationalAgentRunItem:
    agent_slug: str
    site_id: int
    site_name: str
    trigger_reference: str
    status: str
    run_id: int | None = None
    error: str = ""


class OperationalAgentsRunner:
    MAINTENANCE_AGENT_SLUG = "maintenance-agent"
    SCHEDULING_AGENT_SLUG = "scheduling-agent"

    @classmethod
    def run_daily(
        cls,
        *,
        site_id=None,
        target_date=None,
        maintenance_mode="daily_critical_assets",
        dry_run=False,
        force=False,
    ):
        AgentRegistryService.bootstrap_registry()
        run_date = timezone.localdate()
        target_date = target_date or (run_date + timedelta(days=1))
        sites = OperationalSite.objects.select_related("maintenance_client", "maintenance_client__company").filter(is_active=True)
        if site_id:
            sites = sites.filter(pk=site_id)
        sites = list(sites)

        results = []
        for site in sites:
            results.append(
                cls._run_maintenance(
                    site=site,
                    run_date=run_date,
                    maintenance_mode=maintenance_mode,
                    dry_run=dry_run,
                    force=force,
                )
            )
            results.append(
                cls._run_scheduling(
                    site=site,
                    target_date=target_date,
                    dry_run=dry_run,
                    force=force,
                )
            )
        return {
            "run_date": run_date,
            "target_date": target_date,
            "site_count": len(sites),
            "results": results,
            "executed": sum(1 for item in results if item.status == "executed"),
            "skipped": sum(1 for item in results if item.status == "skipped"),
            "planned": sum(1 for item in results if item.status == "planned"),
            "failed": sum(1 for item in results if item.status == "failed"),
        }

    @classmethod
    def _run_maintenance(cls, *, site, run_date, maintenance_mode, dry_run, force):
        trigger_reference = f"operational:maintenance:{maintenance_mode}:{run_date.isoformat()}"
        return cls._run_agent_for_site(
            agent_slug=cls.MAINTENANCE_AGENT_SLUG,
            site=site,
            trigger_reference=trigger_reference,
            dry_run=dry_run,
            force=force,
            runner=lambda: MaintenanceAgentTriggerService.run_site_analysis(
                site=site,
                trigger_type=AgentRun.TriggerType.SCHEDULED,
                trigger_reference=trigger_reference,
            ),
        )

    @classmethod
    def _run_scheduling(cls, *, site, target_date, dry_run, force):
        trigger_reference = f"date:{target_date.isoformat()}"
        return cls._run_agent_for_site(
            agent_slug=cls.SCHEDULING_AGENT_SLUG,
            site=site,
            trigger_reference=trigger_reference,
            dry_run=dry_run,
            force=force,
            runner=lambda: SchedulingAgentTriggerService.run_day_analysis(
                company=site.maintenance_client.company,
                site=site,
                target_date=target_date,
                trigger_type=AgentRun.TriggerType.SCHEDULED,
                trigger_reference=trigger_reference,
            ),
        )

    @classmethod
    def _run_agent_for_site(cls, *, agent_slug, site, trigger_reference, dry_run, force, runner):
        base_result = {
            "agent_slug": agent_slug,
            "site_id": site.id,
            "site_name": site.name,
            "trigger_reference": trigger_reference,
        }
        if dry_run:
            return OperationalAgentRunItem(status="planned", **base_result)
        if not force and cls._has_completed_run(agent_slug=agent_slug, site=site, trigger_reference=trigger_reference):
            return OperationalAgentRunItem(status="skipped", **base_result)
        try:
            run = runner()
        except Exception as exc:
            return OperationalAgentRunItem(status="failed", error=str(exc), **base_result)
        return OperationalAgentRunItem(status="executed", run_id=run.id, **base_result)

    @staticmethod
    def _has_completed_run(*, agent_slug, site, trigger_reference):
        return AgentRun.objects.filter(
            agent__slug=agent_slug,
            site=site,
            trigger_type=AgentRun.TriggerType.SCHEDULED,
            trigger_reference=trigger_reference,
            status=AgentRun.Status.COMPLETED,
        ).exists()
