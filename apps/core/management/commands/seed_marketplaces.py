from django.core.management.base import BaseCommand

from apps.core.bootstrap.common import BootstrapContext, DEMO_PASSWORD
from apps.core.bootstrap.seed_business import seed_marketplaces, seed_smart_site_factory
from apps.core.bootstrap.seed_core import seed_core_platform
from apps.core.bootstrap.seed_operations import seed_marketplace_analytical, seed_marketplace_technicians, seed_smart_system


class Command(BaseCommand):
    help = "Seed dos contextos de marketplace do SMART360."

    def add_arguments(self, parser):
        parser.add_argument("--demo-password", default=DEMO_PASSWORD)

    def handle(self, *args, **options):
        ctx = BootstrapContext(stdout=self.stdout, demo_password=options["demo_password"], verbosity=options["verbosity"])
        seed_core_platform(ctx)
        seed_smart_site_factory(ctx)
        seed_marketplaces(ctx)
        seed_smart_system(ctx)
        seed_marketplace_technicians(ctx)
        seed_marketplace_analytical(ctx)
        self.stdout.write(self.style.SUCCESS("Seed marketplaces concluido."))

