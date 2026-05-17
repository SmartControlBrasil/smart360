from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.ai_agents_center.services.briefing_composer import AIBriefingComposer


class Command(BaseCommand):
    help = "Gera AI Briefings automaticos ou sob demanda."

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            choices=["daily_executive", "daily_field", "daily_client", "weekly_executive"],
            default="daily_executive",
        )

    def handle(self, *args, **options):
        reference_date = timezone.localdate()
        mode = options["mode"]
        if mode == "daily_field":
            briefings = AIBriefingComposer.generate_daily_field_briefings(reference_date=reference_date)
        elif mode == "daily_client":
            briefings = AIBriefingComposer.generate_daily_client_briefings(reference_date=reference_date)
        elif mode == "weekly_executive":
            briefings = AIBriefingComposer.generate_weekly_executive_briefings(reference_date=reference_date)
        else:
            briefings = AIBriefingComposer.generate_daily_executive_briefings(reference_date=reference_date)
        self.stdout.write(self.style.SUCCESS(f"{len(briefings)} briefing(s) generated for mode {mode}"))
