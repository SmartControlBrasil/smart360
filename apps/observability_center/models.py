import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class SystemEventLog(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        CRITICAL = "critical", "Critical"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    event_type = models.CharField(max_length=140, db_index=True)
    source_module = models.CharField(max_length=80, db_index=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="system_event_logs",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="system_event_logs",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="system_event_logs",
        null=True,
        blank=True,
    )
    entity_type = models.CharField(max_length=80, blank=True)
    entity_id = models.CharField(max_length=120, blank=True)
    request_id = models.CharField(max_length=120, blank=True, db_index=True)
    correlation_id = models.CharField(max_length=120, blank=True, db_index=True)
    request_path = models.CharField(max_length=255, blank=True)
    request_method = models.CharField(max_length=12, blank=True)
    message = models.CharField(max_length=255)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "observability_system_event_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["source_module", "event_type"], name="obs_event_src_type_idx"),
            models.Index(fields=["severity", "created_at"], name="obs_event_severity_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.source_module}:{self.event_type}"


class ErrorIncident(models.Model):
    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"
        IGNORED = "ignored", "Ignored"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    incident_key = models.CharField(max_length=180, unique=True)
    source_module = models.CharField(max_length=80, db_index=True)
    error_type = models.CharField(max_length=120, db_index=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MEDIUM, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="error_incidents",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="error_incidents",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="error_incidents",
        null=True,
        blank=True,
    )
    request_id = models.CharField(max_length=120, blank=True, db_index=True)
    correlation_id = models.CharField(max_length=120, blank=True, db_index=True)
    request_path = models.CharField(max_length=255, blank=True)
    message = models.CharField(max_length=255)
    traceback_text = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)
    occurrences_count = models.PositiveIntegerField(default=1)
    resolved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "observability_error_incidents"
        ordering = ["-last_seen_at", "-created_at"]

    def __str__(self) -> str:
        return self.incident_key


class MetricCounter(models.Model):
    class PeriodType(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        TOTAL = "total", "Total"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    metric_key = models.CharField(max_length=140, db_index=True)
    source_module = models.CharField(max_length=80, db_index=True)
    value = models.BigIntegerField(default=0)
    period_type = models.CharField(max_length=20, choices=PeriodType.choices, default=PeriodType.DAILY)
    reference_date = models.DateField(db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "observability_metric_counters"
        ordering = ["-reference_date", "metric_key"]
        constraints = [
            models.UniqueConstraint(
                fields=["metric_key", "source_module", "period_type", "reference_date"],
                name="uniq_obs_metric_counter_scope",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.metric_key}:{self.reference_date}"


class JobExecutionTrace(models.Model):
    class Status(models.TextChoices):
        STARTED = "started", "Started"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    job_name = models.CharField(max_length=160, db_index=True)
    source_module = models.CharField(max_length=80, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="job_execution_traces",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="job_execution_traces",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="job_execution_traces",
        null=True,
        blank=True,
    )
    request_id = models.CharField(max_length=120, blank=True, db_index=True)
    correlation_id = models.CharField(max_length=120, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.STARTED, db_index=True)
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "observability_job_execution_traces"
        ordering = ["-started_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.source_module}:{self.job_name}"


class RequestTrace(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    request_id = models.CharField(max_length=120, unique=True, db_index=True)
    correlation_id = models.CharField(max_length=120, blank=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="request_traces",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="request_traces",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="request_traces",
        null=True,
        blank=True,
    )
    method = models.CharField(max_length=12)
    path = models.CharField(max_length=255, db_index=True)
    status_code = models.PositiveIntegerField(db_index=True)
    duration_ms = models.PositiveIntegerField(default=0)
    source_module = models.CharField(max_length=80, blank=True)
    ip_address = models.CharField(max_length=64, blank=True)
    query_params = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "observability_request_traces"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status_code", "created_at"], name="obs_request_status_idx"),
            models.Index(fields=["company", "site", "created_at"], name="obs_request_scope_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.method} {self.path} [{self.status_code}]"
