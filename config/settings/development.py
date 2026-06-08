from .base import *  # noqa: F403,F401

DEBUG = True
ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = []

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
USE_X_FORWARDED_HOST = False

REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] = [  # noqa: F405
    "rest_framework.permissions.AllowAny",
]

DB_ENGINE = env("DB_ENGINE", default="", cast=str).strip().lower()  # noqa: F405
USE_SQLITE = env("USE_SQLITE", default=True, cast=bool)  # noqa: F405

POSTGRES_IS_CONFIGURED = all(  # noqa: F405
    env_has(var_name)  # noqa: F405
    for var_name in (
        "POSTGRES_HOST",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    )
)

if USE_SQLITE or DB_ENGINE in {"sqlite", "sqlite3"}:
    DATABASES = {"default": sqlite_database_config()}  # noqa: F405

elif DB_ENGINE in {"postgres", "postgresql"}:
    if not POSTGRES_IS_CONFIGURED:
        raise ImproperlyConfigured(  # noqa: F405
            "PostgreSQL foi selecionado, mas as variáveis POSTGRES_HOST, "
            "POSTGRES_DB, POSTGRES_USER e POSTGRES_PASSWORD não estão completas."
        )

    DATABASES = {"default": postgres_database_config()}  # noqa: F405

elif not DB_ENGINE:
    DATABASES = {"default": sqlite_database_config()}  # noqa: F405

else:
    raise ImproperlyConfigured(  # noqa: F405
        "Unsupported DB_ENGINE for development. Use 'sqlite', 'sqlite3', "
        "'postgres', or 'postgresql'."
    )