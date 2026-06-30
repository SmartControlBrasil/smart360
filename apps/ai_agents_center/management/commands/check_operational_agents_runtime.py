from __future__ import annotations

from datetime import timedelta
from importlib import import_module

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from config.celery import app as celery_app

from apps.ai_agents_center.models import AgentActionProposal, AgentDefinition, AgentRun
from apps.ai_agents_center.services.registry import get_agent_class_map


class Command(BaseCommand):
    help = "Diagnostica a configuracao operacional dos agentes sem executar rotinas nem persistir dados."

    PILOT_AGENT_SLUGS = ("maintenance-agent", "scheduling-agent")
    BEAT_ENTRY_KEY = "ai-agents-operational-daily-0630"
    TASK_NAME = "ai_agents_center.run_daily_operational_agents"

    def handle(self, *args, **options):
        self.stdout.write("Operational agents runtime check")
        self._check_agent_registry()
        self._check_task_registration()
        self._check_beat_schedule()
        self._check_timezone()
        self._check_recent_runs()
        self._check_pending_proposals()
        self.stdout.write(self.style.SUCCESS("Operational agents runtime check finished."))

    def _check_agent_registry(self):
        code_registry = set(get_agent_class_map().keys())
        db_registry = set(
            AgentDefinition.objects.filter(slug__in=self.PILOT_AGENT_SLUGS).values_list("slug", flat=True)
        )

        for slug in self.PILOT_AGENT_SLUGS:
            code_status = "present" if slug in code_registry else "missing"
            db_status = "present" if slug in db_registry else "missing"
            line = f"registry {slug} code={code_status} db={db_status}"
            if code_status == "present" and db_status == "present":
                self.stdout.write(self.style.SUCCESS(line))
            else:
                self.stdout.write(self.style.WARNING(line))

    def _check_task_registration(self):
        module = import_module("apps.ai_agents_center.tasks")
        task_callable = getattr(module, "run_daily_operational_agents", None)
        celery_task = celery_app.tasks.get(self.TASK_NAME)

        module_status = "present" if callable(task_callable) else "missing"
        celery_status = "registered" if celery_task is not None else "missing"

        line = f"task {self.TASK_NAME} import={module_status} celery={celery_status}"
        if module_status == "present" and celery_status == "registered":
            self.stdout.write(self.style.SUCCESS(line))
        else:
            self.stdout.write(self.style.WARNING(line))

    def _check_beat_schedule(self):
        beat_entry = celery_app.conf.beat_schedule.get(self.BEAT_ENTRY_KEY, {})
        task_name = beat_entry.get("task")
        schedule = beat_entry.get("schedule")
        hour = getattr(schedule, "_orig_hour", None)
        minute = getattr(schedule, "_orig_minute", None)
        scheduled_time = f"{int(hour):02d}:{int(minute):02d}" if hour is not None and minute is not None else "unknown"
        task_status = "ok" if task_name == self.TASK_NAME else "mismatch"
        schedule_status = "present" if schedule is not None else "missing"

        line = f"beat {self.BEAT_ENTRY_KEY} task={task_status} schedule={schedule_status} time={scheduled_time}"
        if task_status == "ok" and schedule_status == "present":
            self.stdout.write(self.style.SUCCESS(line))
        else:
            self.stdout.write(self.style.WARNING(line))

    def _check_timezone(self):
        celery_timezone = getattr(celery_app.conf, "timezone", None)
        matches = celery_timezone == settings.TIME_ZONE
        line = f"timezone django={settings.TIME_ZONE} celery={celery_timezone} match={'yes' if matches else 'no'}"
        if matches:
            self.stdout.write(self.style.SUCCESS(line))
        else:
            self.stdout.write(self.style.WARNING(line))

    def _check_recent_runs(self):
        latest_run = (
            AgentRun.objects.filter(agent__slug__in=self.PILOT_AGENT_SLUGS)
            .select_related("agent", "company", "site")
            .order_by("-created_at")
            .first()
        )
        if latest_run is None:
            self.stdout.write(self.style.WARNING("agent_runs none_found"))
            return

        age = timezone.now() - latest_run.created_at
        recent = age <= timedelta(hours=24)
        created_at = timezone.localtime(latest_run.created_at).isoformat(timespec="minutes")
        line = (
            f"agent_runs latest={latest_run.agent.slug} status={latest_run.status} "
            f"created_at={created_at} age_hours={age.total_seconds() / 3600:.1f} recent={'yes' if recent else 'no'}"
        )
        if recent:
            self.stdout.write(self.style.SUCCESS(line))
        else:
            self.stdout.write(self.style.WARNING(line))

    def _check_pending_proposals(self):
        cutoff = timezone.now() - timedelta(hours=24)
        old_pending_qs = AgentActionProposal.objects.filter(
            agent_run__agent__slug__in=self.PILOT_AGENT_SLUGS,
            status=AgentActionProposal.Status.PENDING_APPROVAL,
            created_at__lt=cutoff,
        ).select_related("agent_run__agent")
        count = old_pending_qs.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("pending_proposals older_than_24h=0"))
            return

        oldest = old_pending_qs.order_by("created_at").first()
        oldest_age = timezone.now() - oldest.created_at
        line = (
            f"pending_proposals older_than_24h={count} "
            f"oldest={oldest.agent_run.agent.slug}:{oldest.public_id} "
            f"oldest_age_hours={oldest_age.total_seconds() / 3600:.1f}"
        )
        self.stdout.write(self.style.WARNING(line))
