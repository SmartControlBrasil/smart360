from django.core.management.base import BaseCommand

from apps.core.bootstrap.common import BootstrapContext, DEMO_PASSWORD
from apps.core.bootstrap.orchestrator import run_bootstrap


class Command(BaseCommand):
    help = "Bootstrap completo do ecossistema SMART360 com seeders idempotentes e demo data."

    def add_arguments(self, parser):
        parser.add_argument("--demo-password", default=DEMO_PASSWORD, help="Senha padrao para usuarios demo.")

    def handle(self, *args, **options):
        ctx = BootstrapContext(stdout=self.stdout, demo_password=options["demo_password"], verbosity=options["verbosity"])
        run_bootstrap(ctx)
        self.stdout.write(self.style.SUCCESS("SMART360 bootstrap concluido."))

