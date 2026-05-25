from django.conf import settings
from django.urls import NoReverseMatch, reverse


def livia_assistant(request):
    """Expõe flag do widget institucional, branding público por contexto (URL namespace) e modo Caneca."""
    enabled = bool(getattr(settings, "LIVIA_ASSISTANT_ENABLED", False))

    resolver = getattr(request, "resolver_match", None)
    caneca_ns = bool(resolver and resolver.namespace == "caneca_de_garagem")
    caneca_widget_on = bool(getattr(settings, "CANECA_LETICIA_WIDGET_ENABLED", True))
    show_caneca_widget = bool(caneca_ns and caneca_widget_on)

    default = dict(getattr(settings, "LIVIA_CHAT_DEFAULT_BRANDING", {}) or {})

    if show_caneca_widget:
        branding = {**default, **(getattr(settings, "CANECA_LETICIA_BRANDING", {}) or {})}
        try:
            branding["cta_primary_url"] = reverse("caneca_de_garagem:product_list")
            branding["cta_secondary_url"] = reverse("caneca_de_garagem:b2b_quote")
            branding["cta_tertiary_url"] = reverse("caneca_de_garagem:contact")
        except NoReverseMatch:
            branding.setdefault("cta_primary_url", "")
            branding.setdefault("cta_secondary_url", "")
            branding.setdefault("cta_tertiary_url", "")
    else:
        branding = default

    assistant_name = branding.get("assistant_name", "Assistente")
    typing_tpl = branding.get("typing_indicator", "{name} está digitando…")
    branding = {
        **branding,
        "typing_indicator_js": typing_tpl.replace("{name}", assistant_name),
    }

    return {
        "livia_assistant_enabled": enabled,
        "livia_caneca_public_widget": show_caneca_widget,
        "livia_caneca_simple_mode": show_caneca_widget and not enabled,
        "livia_caneca_ai_chat_mode": show_caneca_widget and enabled,
        "livia_chat_branding": branding,
    }
