from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme

CLIENT_PORTAL_URL = "/portal/"
CLIENT_PORTAL_ONLY_GROUP = "client-portal-only"
INTERNAL_PANEL_PREFIXES = ("/ecossistema/", "/app/", "/dashboard/")


def is_client_portal_only_user(user) -> bool:
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return False
    if getattr(user, "user_type", "") == "client":
        return True
    return user.groups.filter(name=CLIENT_PORTAL_ONLY_GROUP).exists()


def is_internal_panel_url(url: str) -> bool:
    path = urlparse(url or "").path or "/"
    return path in {"/ecossistema", "/app", "/dashboard"} or path.startswith(INTERNAL_PANEL_PREFIXES)


def get_post_login_redirect_url(user, next_url: str = "", *, allowed_hosts=None, require_https: bool = False) -> str:
    safe_next = ""
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts=allowed_hosts,
        require_https=require_https,
    ):
        safe_next = next_url

    if is_client_portal_only_user(user):
        if safe_next and safe_next.startswith(CLIENT_PORTAL_URL) and not is_internal_panel_url(safe_next):
            return safe_next
        return CLIENT_PORTAL_URL

    return safe_next or getattr(settings, "LOGIN_REDIRECT_URL", "/ecossistema/")
