from django.conf import settings


def livia_assistant(request):
    return {
        "livia_assistant_enabled": bool(getattr(settings, "LIVIA_ASSISTANT_ENABLED", False)),
    }
