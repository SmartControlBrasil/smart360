import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("smart360")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
app.conf.beat_schedule = {
    "ai-agents-operational-daily-0630": {
        "task": "ai_agents_center.run_daily_operational_agents",
        "schedule": crontab(hour=6, minute=30),
    },
    "ai-briefings-daily-executive-0700": {
        "task": "ai_agents_center.generate_daily_executive_briefings",
        "schedule": crontab(hour=7, minute=0),
    },
    "ai-briefings-daily-field-0700": {
        "task": "ai_agents_center.generate_daily_field_briefings",
        "schedule": crontab(hour=7, minute=0),
    },
    "ai-briefings-daily-client-0700": {
        "task": "ai_agents_center.generate_daily_client_briefings",
        "schedule": crontab(hour=7, minute=0),
    },
    "ai-briefings-weekly-executive-monday-0800": {
        "task": "ai_agents_center.generate_weekly_executive_briefings",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),
    },
}
