from __future__ import annotations


def is_client_portal_only_user(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return False
    if getattr(user, "user_type", "") == "client":
        return True
    return user.groups.filter(name="client-portal-only").exists()
