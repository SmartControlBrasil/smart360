from django.core.management.base import BaseCommand

from apps.ai_agents_center.models import AgentRun
from apps.ai_agents_center.services.maintenance_triggers import MaintenanceAgentTriggerService
from apps.smart_system.models import OperationalSite


class Command(BaseCommand):
    help = "Executa analises programadas do Maintenance Intelligence Agent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            choices=["daily_critical_assets", "weekly_failure_recurrence", "preventive_adherence", "reliability_review"],
            default="daily_critical_assets",
        )
        parser.add_argument("--site-id", type=int, default=None)

    def handle(self, *args, **options):
        queryset = OperationalSite.objects.select_related("maintenance_client", "maintenance_client__company").filter(is_active=True)
        if options["site_id"]:
            queryset = queryset.filter(pk=options["site_id"])

        trigger_reference = f"scheduled:{options['mode']}"
        total_runs = 0
        for site in queryset:
            MaintenanceAgentTriggerService.run_site_analysis(
                site=site,
                trigger_type=AgentRun.TriggerType.SCHEDULED,
                trigger_reference=trigger_reference,
            )
            total_runs += 1
        self.stdout.write(self.style.SUCCESS(f"Maintenance intelligence executed for {total_runs} site(s)."))
