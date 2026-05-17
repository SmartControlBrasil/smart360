import logging
from datetime import date

from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Count, Sum
from django.utils import timezone

from shared_kernel.observability.context import get_correlation_id, get_request_context, get_request_id

from ..models import ErrorIncident, JobExecutionTrace, MetricCounter, RequestTrace, SystemEventLog


logger = logging.getLogger("smart360.observability")


def _current_context():
    request_context = get_request_context()
    return {
        "user": request_context.get("user"),
        "company": request_context.get("company"),
        "site": request_context.get("site"),
        "request_id": get_request_id(),
        "correlation_id": get_correlation_id(),
        "request_path": request_context.get("path", ""),
        "request_method": request_context.get("method", ""),
        "source_module": request_context.get("module", ""),
    }


class SystemEventService:
    @staticmethod
    def log_system_event(
        *,
        event_type,
        source_module,
        message,
        severity=SystemEventLog.Severity.INFO,
        entity_type="",
        entity_id="",
        correlation_id="",
        request_id="",
        payload=None,
        user=None,
        company=None,
        site=None,
        request_path="",
        request_method="",
    ):
        context = _current_context()
        event = SystemEventLog.objects.create(
            event_type=event_type,
            source_module=source_module,
            severity=severity,
            user=user or context["user"],
            company=company or context["company"],
            site=site or context["site"],
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=request_id or context["request_id"],
            correlation_id=correlation_id or get_correlation_id(),
            request_path=request_path or context["request_path"],
            request_method=request_method or context["request_method"],
            message=message,
            payload=payload or {},
        )
        logger.info(
            "system event recorded",
            extra={
                "event": event_type,
                "module_name": source_module,
                "payload": {
                    "severity": severity,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "request_id": event.request_id,
                },
            },
        )
        if not (payload or {}).get("_skip_event_bus"):
            try:
                from apps.integration_bus.services.realtime_bus import RealtimeEventBus

                RealtimeEventBus.publish_from_system_event(system_event=event)
            except Exception:
                logger.exception("failed to mirror system event into realtime event bus")
        return event


class ErrorIncidentService:
    @staticmethod
    @transaction.atomic
    def register_error_incident(
        *,
        incident_key,
        source_module,
        error_type,
        message,
        severity=ErrorIncident.Severity.MEDIUM,
        traceback_text="",
        payload=None,
        notes="",
    ):
        context = _current_context()
        incident, created = ErrorIncident.objects.select_for_update().get_or_create(
            incident_key=incident_key,
            defaults={
                "source_module": source_module,
                "error_type": error_type,
                "severity": severity,
                "user": context["user"],
                "company": context["company"],
                "site": context["site"],
                "request_id": context["request_id"],
                "correlation_id": context["correlation_id"],
                "request_path": context["request_path"],
                "message": message,
                "traceback_text": traceback_text,
                "payload": payload or {},
                "notes": notes,
                "first_seen_at": timezone.now(),
                "last_seen_at": timezone.now(),
            },
        )
        if not created:
            incident.source_module = source_module
            incident.error_type = error_type
            incident.severity = severity
            incident.user = context["user"]
            incident.company = context["company"]
            incident.site = context["site"]
            incident.request_id = context["request_id"]
            incident.correlation_id = context["correlation_id"]
            incident.request_path = context["request_path"]
            incident.message = message
            incident.traceback_text = traceback_text
            incident.payload = payload or {}
            incident.notes = notes or incident.notes
            incident.last_seen_at = timezone.now()
            incident.occurrences_count += 1
            if incident.status == ErrorIncident.Status.RESOLVED:
                incident.status = ErrorIncident.Status.OPEN
                incident.resolved_at = None
            incident.save(
                update_fields=[
                    "source_module",
                    "error_type",
                    "severity",
                    "user",
                    "company",
                    "site",
                    "request_id",
                    "correlation_id",
                    "request_path",
                    "message",
                    "traceback_text",
                    "payload",
                    "notes",
                    "last_seen_at",
                    "occurrences_count",
                    "status",
                    "resolved_at",
                    "updated_at",
                ]
            )
        logger.error(
            "error incident registered",
            extra={
                "event": "error_incident.registered",
                "module_name": source_module,
                "payload": {
                    "incident_key": incident_key,
                    "error_type": error_type,
                    "severity": severity,
                    "created": created,
                },
            },
        )
        return incident


class MetricCounterService:
    @staticmethod
    @transaction.atomic
    def increment_metric(
        *,
        metric_key,
        source_module,
        amount=1,
        period_type=MetricCounter.PeriodType.DAILY,
        reference_date=None,
    ):
        scoped_date = reference_date or date.today()
        counter, _ = MetricCounter.objects.select_for_update().get_or_create(
            metric_key=metric_key,
            source_module=source_module,
            period_type=period_type,
            reference_date=scoped_date,
            defaults={"value": 0},
        )
        counter.value += amount
        counter.save(update_fields=["value", "updated_at"])
        logger.info(
            "metric incremented",
            extra={
                "event": "metric.incremented",
                "module_name": source_module,
                "payload": {
                    "metric_key": metric_key,
                    "amount": amount,
                    "period_type": period_type,
                    "reference_date": str(scoped_date),
                },
            },
        )
        return counter


class JobExecutionTraceService:
    @staticmethod
    def start_job(*, job_name, source_module, correlation_id="", payload=None):
        context = _current_context()
        return JobExecutionTrace.objects.create(
            job_name=job_name,
            source_module=source_module,
            user=context["user"],
            company=context["company"],
            site=context["site"],
            request_id=context["request_id"],
            correlation_id=correlation_id or get_correlation_id(),
            status=JobExecutionTrace.Status.STARTED,
            payload=payload or {},
        )

    @staticmethod
    def complete_job(*, trace, payload=None):
        now = timezone.now()
        trace.status = JobExecutionTrace.Status.COMPLETED
        trace.completed_at = now
        if trace.started_at:
            trace.duration_ms = max(int((now - trace.started_at).total_seconds() * 1000), 0)
        if payload is not None:
            trace.payload = payload
        trace.error_message = ""
        trace.save(update_fields=["status", "completed_at", "duration_ms", "payload", "error_message", "updated_at"])
        logger.info(
            "job completed",
            extra={
                "event": "jobs.completed",
                "module_name": trace.source_module,
                "payload": {"job_name": trace.job_name, "duration_ms": trace.duration_ms},
            },
        )
        return trace

    @staticmethod
    def fail_job(*, trace, error_message, payload=None):
        now = timezone.now()
        trace.status = JobExecutionTrace.Status.FAILED
        trace.failed_at = now
        if trace.started_at:
            trace.duration_ms = max(int((now - trace.started_at).total_seconds() * 1000), 0)
        if payload is not None:
            trace.payload = payload
        trace.error_message = error_message
        trace.save(update_fields=["status", "failed_at", "duration_ms", "payload", "error_message", "updated_at"])
        logger.error(
            "job failed",
            extra={
                "event": "jobs.failed",
                "module_name": trace.source_module,
                "payload": {"job_name": trace.job_name, "duration_ms": trace.duration_ms, "error_message": error_message},
            },
        )
        return trace


class RequestTraceService:
    @staticmethod
    def record_request(
        *,
        request_id,
        correlation_id,
        method,
        path,
        status_code,
        duration_ms,
        user=None,
        company=None,
        site=None,
        source_module="",
        ip_address="",
        query_params=None,
        metadata=None,
    ):
        trace = RequestTrace.objects.create(
            request_id=request_id,
            correlation_id=correlation_id,
            user=user,
            company=company,
            site=site,
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            source_module=source_module,
            ip_address=ip_address,
            query_params=query_params or {},
            metadata=metadata or {},
        )
        MetricCounterService.increment_metric(metric_key="http.requests.total", source_module="platform", period_type=MetricCounter.PeriodType.DAILY)
        if status_code >= 400:
            MetricCounterService.increment_metric(metric_key=f"http.responses.{status_code}", source_module="platform", period_type=MetricCounter.PeriodType.DAILY)
        return trace


class HealthcheckService:
    @staticmethod
    def liveness():
        return {
            "status": "ok",
            "service": "smart360",
            "environment": settings.ENVIRONMENT,
            "version": getattr(settings, "APP_VERSION", "1.0.0"),
        }

    @staticmethod
    def _database_status():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return {"status": "ok", "engine": settings.DATABASES["default"]["ENGINE"]}
        except Exception as exc:  # pragma: no cover - defensive path
            return {"status": "error", "engine": settings.DATABASES["default"]["ENGINE"], "message": str(exc)}

    @staticmethod
    def _cache_status():
        cache_key = "smart360:healthcheck"
        try:
            cache.set(cache_key, "ok", timeout=10)
            cache_value = cache.get(cache_key)
            backend = settings.CACHES["default"]["BACKEND"]
            return {"status": "ok" if cache_value == "ok" else "error", "backend": backend}
        except Exception as exc:  # pragma: no cover - defensive path
            return {
                "status": "error",
                "backend": settings.CACHES["default"]["BACKEND"],
                "message": str(exc),
            }

    @staticmethod
    def _celery_status():
        return {
            "status": "configured" if settings.CELERY_BROKER_URL else "not_configured",
            "broker_url": settings.CELERY_BROKER_URL,
            "result_backend": settings.CELERY_RESULT_BACKEND,
        }

    @staticmethod
    def _storage_status():
        try:
            default_storage.exists("")
            return {"status": "ok", "backend": default_storage.__class__.__name__}
        except Exception as exc:  # pragma: no cover
            return {"status": "error", "backend": default_storage.__class__.__name__, "message": str(exc)}

    @staticmethod
    def _pdf_status():
        try:
            import reportlab  # noqa: F401

            return {"status": "ok", "backend": "reportlab"}
        except Exception as exc:  # pragma: no cover
            return {"status": "error", "backend": "reportlab", "message": str(exc)}

    @staticmethod
    def _migrations_status():
        try:
            executor = MigrationExecutor(connection)
            pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
            return {"status": "ok" if not pending else "warning", "pending_migrations": len(pending)}
        except Exception as exc:  # pragma: no cover
            return {"status": "error", "message": str(exc)}

    @staticmethod
    def readiness():
        checks = {
            "database": HealthcheckService._database_status(),
            "cache": HealthcheckService._cache_status(),
            "storage": HealthcheckService._storage_status(),
            "pdf": HealthcheckService._pdf_status(),
            "migrations": HealthcheckService._migrations_status(),
            "celery": HealthcheckService._celery_status(),
        }
        if any(item["status"] == "error" for item in checks.values()):
            status_value = "degraded"
        elif any(item["status"] == "warning" for item in checks.values()):
            status_value = "warning"
        else:
            status_value = "ok"
        return {
            "status": status_value,
            "service": "smart360",
            "environment": settings.ENVIRONMENT,
            "version": getattr(settings, "APP_VERSION", "1.0.0"),
            "checks": checks,
        }

    @staticmethod
    def summary():
        summary = HealthcheckService.readiness()
        summary["liveness"] = HealthcheckService.liveness()
        return summary


class ObservabilitySummaryService:
    @staticmethod
    def health_summary():
        return HealthcheckService.summary()

    @staticmethod
    def error_summary():
        grouped = (
            ErrorIncident.objects.values("status", "severity")
            .annotate(total=Count("id"))
            .order_by("status", "severity")
        )
        return {
            "total_open": ErrorIncident.objects.filter(status=ErrorIncident.Status.OPEN).count(),
            "total_acknowledged": ErrorIncident.objects.filter(status=ErrorIncident.Status.ACKNOWLEDGED).count(),
            "by_status_and_severity": list(grouped),
        }

    @staticmethod
    def metrics_summary():
        today = date.today()
        counters = (
            MetricCounter.objects.filter(reference_date=today)
            .values("source_module")
            .annotate(total_value=Sum("value"), counters=Count("id"))
            .order_by("source_module")
        )
        return {
            "reference_date": today,
            "modules": list(counters),
        }

    @staticmethod
    def platform_summary():
        recent_errors = list(
            RequestTrace.objects.filter(status_code__gte=400)
            .values("path", "status_code", "company__name")
            .order_by("-created_at")[:5]
        )
        critical_events = list(
            SystemEventLog.objects.filter(severity__in=[SystemEventLog.Severity.ERROR, SystemEventLog.Severity.CRITICAL])
            .values("event_type", "source_module", "message", "created_at")[:6]
        )
        latest_audits = list(
            SystemEventLog.objects.filter(event_type__startswith="audit.")
            .values("event_type", "source_module", "message", "company__name", "created_at")[:6]
        )
        recent_jobs = list(
            JobExecutionTrace.objects.values("job_name", "source_module", "status", "duration_ms", "started_at")[:6]
        )
        billing_risk = list(
            SystemEventLog.objects.filter(source_module="billing").values("event_type", "message", "company__name", "created_at")[:5]
        )
        return {
            "health": HealthcheckService.summary(),
            "recent_errors": recent_errors,
            "critical_events": critical_events,
            "latest_audits": latest_audits,
            "recent_jobs": recent_jobs,
            "billing_risk": billing_risk,
        }
