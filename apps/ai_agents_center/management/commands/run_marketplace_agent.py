from django.core.management.base import BaseCommand

from apps.ai_agents_center.models import AgentRun
from apps.ai_agents_center.services.marketplace_triggers import MarketplaceAllocationTriggerService
from apps.marketplace_technicians.models import TechnicianServiceRequest


class Command(BaseCommand):
    help = "Executa analises programadas do Marketplace Allocation Agent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            choices=["open_requests", "unassigned_requests", "sla_risk", "regional_backlog"],
            default="open_requests",
        )
        parser.add_argument("--company-id", type=int, default=None)

    def handle(self, *args, **options):
        queryset = TechnicianServiceRequest.objects.select_related("requester_company", "related_site").filter(
            status__in=[
                TechnicianServiceRequest.Status.OPEN,
                TechnicianServiceRequest.Status.MATCHING,
                TechnicianServiceRequest.Status.OFFERS_RECEIVED,
            ]
        )
        if options["company_id"]:
            queryset = queryset.filter(requester_company_id=options["company_id"])

        seen = set()
        total_runs = 0
        for request in queryset:
            if not request.requester_company_id:
                continue
            key = (request.requester_company_id, request.related_site_id)
            if key in seen and options["mode"] != "regional_backlog":
                continue
            seen.add(key)
            MarketplaceAllocationTriggerService.run_queue_analysis(
                company=request.requester_company,
                site=request.related_site if options["mode"] == "regional_backlog" else None,
                trigger_type=AgentRun.TriggerType.SCHEDULED,
                trigger_reference=f"site:{request.related_site.code}" if request.related_site_id and options["mode"] == "regional_backlog" else "scheduled:marketplace-queue",
            )
            total_runs += 1

        self.stdout.write(self.style.SUCCESS(f"Marketplace allocation agent executed for {total_runs} scope(s)."))
