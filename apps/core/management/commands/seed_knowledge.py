from django.core.management.base import BaseCommand

from apps.core.bootstrap.common import BootstrapContext, DEMO_PASSWORD
from apps.core.bootstrap.seed_core import seed_core_platform
from apps.core.bootstrap.seed_operations import seed_knowledge


class Command(BaseCommand):
    help = "Seed do Knowledge Engine."

    def add_arguments(self, parser):
        parser.add_argument("--demo-password", default=DEMO_PASSWORD)

    def handle(self, *args, **options):
        ctx = BootstrapContext(stdout=self.stdout, demo_password=options["demo_password"], verbosity=options["verbosity"])
        seed_core_platform(ctx)
        seed_knowledge(ctx)
        self.stdout.write(self.style.SUCCESS("Seed knowledge concluido."))

