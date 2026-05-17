from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.ai_agents_center.models import AgentRun
from apps.ai_agents_center.services.profitability_triggers import ProfitabilityAgentTriggerService
from apps.smart_system.models import OperationalSite


class Command(BaseCommand):
    help = "Executa analises programadas do Profitability Agent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            choices=["weekly_contracts", "monthly_clients", "monthly_margin", "regional_operation"],
            default="monthly_clients",
        )
        parser.add_argument("--site-id", type=int, default=None)
        parser.add_argument("--date", type=str, default=None)

    def handle(self, *args, **options):
        reference_date = timezone.localdate()
        if options["date"]:
            reference_date = datetime.strptime(options["date"], "%Y-%m-%d").date()

        queryset = OperationalSite.objects.select_related("maintenance_client", "maintenance_client__company").filter(is_active=True)
        if options["site_id"]:
            queryset = queryset.filter(pk=options["site_id"])

        total_runs = 0
        for site in queryset:
            ProfitabilityAgentTriggerService.run_company_analysis(
                company=site.maintenance_client.company,
                site=site if options["mode"] == "regional_operation" else None,
                trigger_type=AgentRun.TriggerType.SCHEDULED,
                trigger_reference=(
                    f"site:{site.code}" if options["mode"] == "regional_operation" else f"date:{reference_date.isoformat()}"
                ),
            )
            total_runs += 1
        self.stdout.write(self.style.SUCCESS(f"Profitability agent executed for {total_runs} site(s)."))
