from celery import shared_task
from django.utils import timezone

from apps.ai_agents_center.services.briefing_composer import AIBriefingComposer


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
