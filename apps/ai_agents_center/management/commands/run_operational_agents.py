from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from apps.ai_agents_center.services.operational_runner import OperationalAgentsRunner


class Command(BaseCommand):
    help = "Executa a rotina operacional de maintenance-agent e scheduling-agent para o piloto."

    def add_arguments(self, parser):
        parser.add_argument("--site-id", type=int, default=None)
        parser.add_argument("--date", type=str, default=None, help="Data alvo da agenda no formato YYYY-MM-DD.")
        parser.add_argument(
            "--maintenance-mode",
            choices=["daily_critical_assets", "weekly_failure_recurrence", "preventive_adherence", "reliability_review"],
            default="daily_critical_assets",
        )
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--force", action="store_true", help="Reexecuta mesmo se ja houver AgentRun concluido para o mesmo site/data.")

    def handle(self, *args, **options):
        target_date = None
        if options["date"]:
            target_date = datetime.strptime(options["date"], "%Y-%m-%d").date()

        summary = OperationalAgentsRunner.run_daily(
            site_id=options["site_id"],
            target_date=target_date,
            maintenance_mode=options["maintenance_mode"],
            dry_run=options["dry_run"],
            force=options["force"],
        )
        for item in summary["results"]:
            suffix = f" run={item.run_id}" if item.run_id else ""
            if item.error:
                suffix = f" error={item.error}"
            self.stdout.write(
                f"{item.status.upper()} {item.agent_slug} site={item.site_id} ref={item.trigger_reference}{suffix}"
            )

        message = (
            "Operational agents: "
            f"sites={summary['site_count']} executed={summary['executed']} "
            f"skipped={summary['skipped']} planned={summary['planned']} failed={summary['failed']}"
        )
        if summary["failed"]:
            self.stderr.write(self.style.ERROR(message))
            raise CommandError("Operational agents routine finished with failures.")
        self.stdout.write(self.style.SUCCESS(message))
