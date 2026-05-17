from django.core.management.base import BaseCommand

from apps.ai_agents_center.models import AgentRun
from apps.ai_agents_center.services.anomaly_triggers import AnomalyAgentTriggerService
from apps.companies.models import Company


class Command(BaseCommand):
    help = "Executa analises programadas do Anomaly Detection Agent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            choices=["daily_operations", "weekly_failures", "marketplace", "monthly_financial"],
            default="daily_operations",
        )
        parser.add_argument("--company-id", type=int, default=None)

    def handle(self, *args, **options):
        companies = Company.objects.all().order_by("name")
        if options["company_id"]:
            companies = companies.filter(id=options["company_id"])

        total_runs = 0
        for company in companies:
            trigger_reference = {
                "daily_operations": "scheduled:daily-operations",
                "weekly_failures": "scheduled:weekly-failure-patterns",
                "marketplace": "scheduled:marketplace-anomaly-review",
                "monthly_financial": "scheduled:monthly-financial-anomalies",
            }[options["mode"]]
            AnomalyAgentTriggerService.run_company_analysis(
                company=company,
                trigger_type=AgentRun.TriggerType.SCHEDULED,
                trigger_reference=trigger_reference,
            )
            total_runs += 1

        self.stdout.write(self.style.SUCCESS(f"Anomaly detection agent executed for {total_runs} company scope(s)."))
