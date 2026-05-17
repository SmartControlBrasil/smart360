from django.apps import AppConfig


class AdminShellConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.admin_shell"
    verbose_name = "Admin Shell"
