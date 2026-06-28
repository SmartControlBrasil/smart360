import logging

from celery import shared_task
from django.utils import timezone

from apps.ai_agents_center.services.briefing_composer import AIBriefingComposer
from apps.ai_agents_center.services.operational_runner import OperationalAgentsRunner


logger = logging.getLogger(__name__)


def _serialize_operational_agents_summary(summary):
    return {
        **summary,
        "run_date": summary["run_date"].isoformat(),
        "target_date": summary["target_date"].isoformat(),
        "results": [
            {
                "agent_slug": item.agent_slug,
                "site_id": item.site_id,
                "site_name": item.site_name,
                "trigger_reference": item.trigger_reference,
                "status": item.status,
                "run_id": item.run_id,
                "error": item.error,
            }
            for item in summary["results"]
        ],
    }


@shared_task(name="ai_agents_center.generate_daily_executive_briefings")
def generate_daily_executive_briefings():
    return [str(item.public_id) for item in AIBriefingComposer.generate_daily_executive_briefings(reference_date=timezone.localdate())]


@shared_task(name="ai_agents_center.generate_daily_field_briefings")
def generate_daily_field_briefings():
    return [str(item.public_id) for item in AIBriefingComposer.generate_daily_field_briefings(reference_date=timezone.localdate())]


@shared_task(name="ai_agents_center.generate_daily_client_briefings")
def generate_daily_client_briefings():
    return [str(item.public_id) for item in AIBriefingComposer.generate_daily_client_briefings(reference_date=timezone.localdate())]


@shared_task(name="ai_agents_center.generate_weekly_executive_briefings")
def generate_weekly_executive_briefings():
    return [str(item.public_id) for item in AIBriefingComposer.generate_weekly_executive_briefings(reference_date=timezone.localdate())]


@shared_task(name="ai_agents_center.run_daily_operational_agents")
def run_daily_operational_agents(dry_run=False, force=False):
    logger.info("Starting daily operational agents task.", extra={"dry_run": dry_run, "force": force})
    try:
        summary = OperationalAgentsRunner.run_daily(dry_run=dry_run, force=force)
    except Exception:
        logger.exception("Daily operational agents task failed.")
        return {"status": "failed", "error": "unexpected_exception"}

    serialized = _serialize_operational_agents_summary(summary)
    if summary["failed"]:
        logger.error("Daily operational agents task finished with agent failures.", extra=serialized)
        serialized["status"] = "failed"
        return serialized

    logger.info("Daily operational agents task finished.", extra=serialized)
    serialized["status"] = "completed"
    return serialized
