from django.core.management.base import BaseCommand

from apps.access_control_center.services.smart_system_access import bootstrap_smart_system_access


class Command(BaseCommand):
    help = "Cria e atualiza perfis, permissões e vínculos padrão do Smart System."

    def handle(self, *args, **options):
        summary = bootstrap_smart_system_access()
        self.stdout.write(self.style.SUCCESS("Smart System access matrix aplicada com sucesso."))
        for key, value in summary.items():
            self.stdout.write(f"- {key}: {value}")
