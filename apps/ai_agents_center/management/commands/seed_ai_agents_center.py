from django.core.management.base import BaseCommand

from apps.ai_agents_center.services.registry import AgentRegistryService


class Command(BaseCommand):
    help = "Bootstrap AI Agents Center registry and execution policies."

    def handle(self, *args, **options):
        definitions = AgentRegistryService.bootstrap_registry()
        self.stdout.write(self.style.SUCCESS(f"{len(definitions)} agents bootstrapped."))
