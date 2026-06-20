from django.core.management.base import BaseCommand

from apps.marketplace_ecom.services.catalog_seed import seed_technical_catalog_from_static


class Command(BaseCommand):
    help = "Importa ou atualiza produtos do catálogo técnico a partir do seed em catalog.py (sem duplicar slug)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--starting-order",
            type=int,
            default=10,
            help="Ordem inicial de exibição para novos registros.",
        )
        parser.add_argument(
            "--step",
            type=int,
            default=10,
            help="Incremento da ordem de exibição entre produtos.",
        )

    def handle(self, *args, **options):
        result = seed_technical_catalog_from_static(
            starting_order=options["starting_order"],
            step=options["step"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                "Catálogo técnico seed concluído: "
                f"{result['created']} criados, {result['updated']} atualizados, "
                f"{result['total']} no seed."
            )
        )
