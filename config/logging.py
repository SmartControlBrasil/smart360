import json
import logging
from datetime import datetime, timezone

from django.conf import settings

from shared_kernel.observability.context import get_correlation_id, get_request_context, get_request_id


SENSITIVE_KEYS = {"password", "token", "access", "authorization", "secret", "api_key", "refresh"}


def sanitize_payload(payload):
    if isinstance(payload, dict):
        sanitized = {}
        for key, value in payload.items():
            if str(key).lower() in SENSITIVE_KEYS:
                sanitized[key] = "***"
            else:
                sanitized[key] = sanitize_payload(value)
        return sanitized
    if isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    return payload


class Smart360JsonFormatter(logging.Formatter):
    """JSON estruturado; herda logging.Formatter para expor formatException em exc_info."""

    def format(self, record):
        request_context = get_request_context()
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "service": getattr(record, "service", "smart360"),
            "environment": getattr(record, "environment", settings.ENVIRONMENT),
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", get_correlation_id() or "-"),
            "request_id": getattr(record, "request_id", get_request_id() or "-"),
            "user_id": getattr(record, "user_id", request_context.get("user_id", "")),
            "company_id": getattr(record, "company_id", request_context.get("company_id", "")),
            "site_id": getattr(record, "site_id", request_context.get("site_id", "")),
            "path": getattr(record, "path", request_context.get("path", "")),
            "method": getattr(record, "method", request_context.get("method", "")),
            "module": getattr(record, "module_name", request_context.get("module", "")),
            "event": getattr(record, "event", ""),
        }
        if hasattr(record, "payload"):
            payload["payload"] = sanitize_payload(record.payload)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True, default=str)


class Smart360ContextFilter:
    def filter(self, record):
        request_context = get_request_context()
        record.correlation_id = get_correlation_id() or "-"
        record.request_id = get_request_id() or "-"
        record.service = "smart360"
        record.environment = settings.ENVIRONMENT
        record.user_id = request_context.get("user_id", "")
        record.company_id = request_context.get("company_id", "")
        record.site_id = request_context.get("site_id", "")
        record.path = request_context.get("path", "")
        record.method = request_context.get("method", "")
        record.module_name = request_context.get("module", "")
        return True


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "smart360_context": {
            "()": "config.logging.Smart360ContextFilter",
        },
    },
    "formatters": {
        "structured_console": {
            "()": "config.logging.Smart360JsonFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["smart360_context"],
            "formatter": "structured_console",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "smart360": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "smart360.observability": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
