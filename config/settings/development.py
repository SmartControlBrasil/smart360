from .base import *  # noqa: F403,F401

DEBUG = True
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = []  # noqa: F405
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
SECURE_SSL_REDIRECT = False  # noqa: F405
SESSION_COOKIE_SECURE = False  # noqa: F405
CSRF_COOKIE_SECURE = False  # noqa: F405
USE_X_FORWARDED_HOST = False  # noqa: F405

REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = [  # noqa: F405
    "rest_framework.permissions.AllowAny",
]

DB_ENGINE = env("DB_ENGINE", default="", cast=str).strip().lower()  # noqa: F405
USE_SQLITE = env("USE_SQLITE", default="False", cast=bool)  # noqa: F405
POSTGRES_IS_CONFIGURED = any(  # noqa: F405
    env_has(var_name)  # noqa: F405
    for var_name in ("POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
)

if USE_SQLITE or DB_ENGINE in {"sqlite", "sqlite3"} or (not DB_ENGINE and not POSTGRES_IS_CONFIGURED):
    DATABASES = {"default": sqlite_database_config()}  # noqa: F405
elif DB_ENGINE in {"", "postgres", "postgresql"}:
    DATABASES = {"default": postgres_database_config()}  # noqa: F405
else:
    raise ImproperlyConfigured(  # noqa: F405
        "Unsupported DB_ENGINE for development. Use 'sqlite', 'sqlite3', 'postgres', or 'postgresql'."
    )
