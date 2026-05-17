from django.apps import AppConfig
from django.db.models.signals import post_migrate


def bootstrap_roles(sender, **kwargs):
    from .services.bootstrap import ensure_default_roles

    ensure_default_roles()


class RolesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.roles"
    verbose_name = "Roles"

    def ready(self):
        post_migrate.connect(bootstrap_roles, sender=self)
