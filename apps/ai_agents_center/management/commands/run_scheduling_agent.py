from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.ai_agents_center.models import AgentRun
from apps.ai_agents_center.services.scheduling_triggers import SchedulingAgentTriggerService
from apps.smart_system.models import OperationalSite


class Command(BaseCommand):
    help = "Executa analises programadas do Scheduling Optimization Agent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            choices=["next_day", "start_of_day", "weekly_routes", "unassigned_backlog"],
            default="next_day",
        )
        parser.add_argument("--site-id", type=int, default=None)
        parser.add_argument("--date", type=str, default=None)

    def handle(self, *args, **options):
        target_date = timezone.localdate()
        if options["mode"] == "next_day":
            target_date = target_date + timedelta(days=1)
        if options["date"]:
            target_date = timezone.datetime.strptime(options["date"], "%Y-%m-%d").date()

        queryset = OperationalSite.objects.select_related("maintenance_client", "maintenance_client__company").filter(is_active=True)
        if options["site_id"]:
            queryset = queryset.filter(pk=options["site_id"])

        total_runs = 0
        for site in queryset:
            SchedulingAgentTriggerService.run_for_site(
                site=site,
                target_date=target_date,
                trigger_type=AgentRun.TriggerType.SCHEDULED,
            )
            total_runs += 1
        self.stdout.write(self.style.SUCCESS(f"Scheduling optimization executed for {total_runs} site(s) on {target_date.isoformat()}."))
