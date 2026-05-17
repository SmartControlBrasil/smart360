from apps.roles.models import Role


DEFAULT_ROLES = [
    {"code": "platform_admin", "label": "Platform Admin", "scope": Role.Scope.PLATFORM},
    {"code": "company_owner", "label": "Company Owner", "scope": Role.Scope.COMPANY},
    {"code": "company_manager", "label": "Company Manager", "scope": Role.Scope.COMPANY},
    {"code": "company_member", "label": "Company Member", "scope": Role.Scope.COMPANY},
]


def ensure_default_roles():
    for role_data in DEFAULT_ROLES:
        Role.objects.get_or_create(code=role_data["code"], defaults=role_data)
