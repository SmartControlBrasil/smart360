from django.core.management.base import BaseCommand

from apps.core.bootstrap.common import BootstrapContext, DEMO_PASSWORD
from apps.core.bootstrap.seed_core import seed_core_platform
from apps.core.bootstrap.seed_transversal import seed_billing


class Command(BaseCommand):
    help = "Seed do Billing."

    def add_arguments(self, parser):
        parser.add_argument("--demo-password", default=DEMO_PASSWORD)

    def handle(self, *args, **options):
        ctx = BootstrapContext(stdout=self.stdout, demo_password=options["demo_password"], verbosity=options["verbosity"])
        seed_core_platform(ctx)
        seed_billing(ctx)
        self.stdout.write(self.style.SUCCESS("Seed billing concluido."))

