import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from config.logging import LOGGING


BASE_DIR = Path(__file__).resolve().parents[2]


def _read_env_file():
    env_path = BASE_DIR / ".env"
    env_map = {}

    if env_path.exists():
        for line in env_path.read_text().splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            env_key, env_value = stripped.split("=", 1)
            env_map[env_key.strip()] = env_value.strip().strip("'").strip('"')

    return env_map


_ENV_FILE_VALUES = _read_env_file()


def env(key: str, default=None, cast=str):
    raw = _ENV_FILE_VALUES.get(key)
    if raw is None:
        raw = os.environ.get(key, default)

    if raw is None:
        raise ImproperlyConfigured(f"Missing required environment variable: {key}")

    if cast is bool:
        return str(raw).lower() in {"1", "true", "yes", "on"}
    if cast is int:
        return int(raw)
    if cast is float:
        return float(raw)
    if cast is list:
        return [item.strip() for item in str(raw).split(",") if item.strip()]
    return raw


def env_has(key: str) -> bool:
    return key in _ENV_FILE_VALUES or key in os.environ


def postgres_database_config():
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", default="smart360"),
        "USER": env("POSTGRES_USER", default="smart360"),
        "PASSWORD": env("POSTGRES_PASSWORD", default="smart360"),
        "HOST": env("POSTGRES_HOST", default="db"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        "CONN_MAX_AGE": env("POSTGRES_CONN_MAX_AGE", default="60", cast=int),
    }


def sqlite_database_config():
    return {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }


SECRET_KEY = env("DJANGO_SECRET_KEY", default="change-me-in-production")
DEBUG = env("DJANGO_DEBUG", default="False", cast=bool)
LIVIA_ASSISTANT_ENABLED = env("LIVIA_ASSISTANT_ENABLED", default="False", cast=bool)
LIVIA_AI_PROVIDER = env("LIVIA_AI_PROVIDER", default="fallback")
LIVIA_AI_MODEL = env("LIVIA_AI_MODEL", default="gpt-4o-mini")
LIVIA_AI_TEMPERATURE = env("LIVIA_AI_TEMPERATURE", default="0.4", cast=float)
LIVIA_AI_MAX_TOKENS = env("LIVIA_AI_MAX_TOKENS", default="500", cast=int)
ENVIRONMENT = env("DJANGO_ENV", default="development")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=list)
CSRF_TRUSTED_ORIGINS = env("DJANGO_CSRF_TRUSTED_ORIGINS", default="", cast=list)

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "drf_spectacular",
    "django_filters",
    "rest_framework.authtoken",
]

LOCAL_APPS = [
    "apps.core.apps.CoreConfig",
    "apps.institutional.apps.InstitutionalConfig",
    "apps.livia_assistant.apps.LiviaAssistantConfig",
    "apps.users.apps.UsersConfig",
    "apps.companies.apps.CompaniesConfig",
    "apps.roles.apps.RolesConfig",
    "apps.audit.apps.AuditConfig",
    "apps.smart_site_factory.apps.SmartSiteFactoryConfig",
    "apps.growth_engine.apps.GrowthEngineConfig",
    "apps.market_core.apps.MarketCoreConfig",
    "apps.caneca_de_garagem.apps.CanecaDeGaragemConfig",
    "apps.smart_system.apps.SmartSystemConfig",
    "apps.marketplace_technicians.apps.MarketplaceTechniciansConfig",
    "apps.marketplace_analytical.apps.MarketplaceAnalyticalConfig",
    "apps.knowledge_engine.apps.KnowledgeEngineConfig",
    "apps.technical_portal.apps.TechnicalPortalConfig",
    "apps.analytics_platform.apps.AnalyticsPlatformConfig",
    "apps.integration_bus.apps.IntegrationBusConfig",
    "apps.billing.apps.BillingConfig",
    "apps.notification_center.apps.NotificationCenterConfig",
    "apps.identity.apps.IdentityConfig",
    "apps.backoffice.apps.BackofficeConfig",
    "apps.files_center.apps.FilesCenterConfig",
    "apps.global_search.apps.GlobalSearchConfig",
    "apps.reporting_center.apps.ReportingCenterConfig",
    "apps.configuration_center.apps.ConfigurationCenterConfig",
    "apps.scheduling_center.apps.SchedulingCenterConfig",
    "apps.access_control_center.apps.AccessControlCenterConfig",
    "apps.ai_automation_center.apps.AiAutomationCenterConfig",
    "apps.ai_agents_center.apps.AiAgentsCenterConfig",
    "apps.ai_decision_engine.apps.AiDecisionEngineConfig",
    "apps.ai_simulation_engine.apps.AiSimulationEngineConfig",
    "apps.ai_optimization_loop.apps.AiOptimizationLoopConfig",
    "apps.ai_policy_studio.apps.AiPolicyStudioConfig",
    "apps.ai_experimentation_framework.apps.AiExperimentationFrameworkConfig",
    "apps.ai_autonomous_ops.apps.AiAutonomousOpsConfig",
    "apps.ai_digital_twin.apps.AiDigitalTwinConfig",
    "apps.ai_knowledge_graph.apps.AiKnowledgeGraphConfig",
    "apps.ai_voice_ops.apps.AiVoiceOpsConfig",
    "apps.observability_center.apps.ObservabilityCenterConfig",
    "apps.public_api.apps.PublicApiConfig",
    "apps.admin_shell.apps.AdminShellConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "shared_kernel.observability.middleware.CorrelationIdMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.livia_assistant.context_processors.livia_assistant",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": postgres_database_config(),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = env("DJANGO_LANGUAGE_CODE", default="pt-br")
TIME_ZONE = env("DJANGO_TIME_ZONE", default="America/Sao_Paulo")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

APP_VERSION = env("SMART360_APP_VERSION", default="1.0.0")
APP_DOMAIN = env("SMART360_APP_DOMAIN", default="localhost")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "users.User"
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/ecossistema/"
LOGOUT_REDIRECT_URL = "/login/"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "config.schema.Smart360AutoSchema",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
        "rest_framework.filters.SearchFilter",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.identity.authentication.IdentityTokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": env("API_PAGE_SIZE", default="25", cast=int),
    "DEFAULT_THROTTLE_RATES": {
        "public_api_burst": env("PUBLIC_API_BURST_RATE", default="60/minute"),
        "public_api_sustained": env("PUBLIC_API_SUSTAINED_RATE", default="1000/day"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "SMART360 API",
    "DESCRIPTION": (
        "API modular do ecossistema SMART360. Esta documentacao consolida os bounded contexts "
        "do core platform, operacao, marketplaces, billing, configuracao, IA e servicos transversais."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "CONTACT": {
        "name": "SMART360 Engineering",
        "email": "engineering@smart360.local",
    },
    "TAGS": __import__("config.schema", fromlist=["SMART360_TAGS"]).SMART360_TAGS,
    "POSTPROCESSING_HOOKS": [
        "config.schema.smart360_postprocess_schema",
    ],
    "SCHEMA_PATH_PREFIX": r"/api(?:/v1|/public/v1)",
    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "docExpansion": "list",
    },
}

REDIS_URL = env("REDIS_URL", default="redis://redis:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="mailhog")
EMAIL_PORT = env("EMAIL_PORT", default="1025", cast=int)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env("EMAIL_USE_TLS", default="False", cast=bool)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@smart360.local")
CONTACT_EMAIL = env("CONTACT_EMAIL", default="contato@smartcontrolbrasil.com.br")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = env("DJANGO_USE_X_FORWARDED_HOST", default="False", cast=bool)
SECURE_SSL_REDIRECT = env("DJANGO_SECURE_SSL_REDIRECT", default="False", cast=bool)
SESSION_COOKIE_SECURE = env("DJANGO_SESSION_COOKIE_SECURE", default="False", cast=bool)
CSRF_COOKIE_SECURE = env("DJANGO_CSRF_COOKIE_SECURE", default="False", cast=bool)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

INTERNAL_MODULES = {
    "core_platform": "apps.core",
    "smart_site_factory": "apps.smart_site_factory",
    "growth_engine": "apps.growth_engine",
    "caneca_de_garagem": "apps.caneca_de_garagem",
    "smart_system": "apps.smart_system",
    "marketplace_technicians": "apps.marketplace_technicians",
    "marketplace_analytical": "apps.marketplace_analytical",
    "knowledge_engine": "apps.knowledge_engine",
    "analytics_platform": "apps.analytics_platform",
    "integration_bus": "apps.integration_bus",
    "billing": "apps.billing",
    "notification_center": "apps.notification_center",
    "identity": "apps.identity",
    "backoffice": "apps.backoffice",
    "files_center": "apps.files_center",
    "global_search": "apps.global_search",
    "reporting_center": "apps.reporting_center",
    "configuration_center": "apps.configuration_center",
    "scheduling_center": "apps.scheduling_center",
    "access_control_center": "apps.access_control_center",
    "ai_automation_center": "apps.ai_automation_center",
    "ai_decision_engine": "apps.ai_decision_engine",
    "ai_simulation_engine": "apps.ai_simulation_engine",
    "ai_optimization_loop": "apps.ai_optimization_loop",
    "observability_center": "apps.observability_center",
}
