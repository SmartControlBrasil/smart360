import uuid

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class IntegrationEvent(models.Model):
    class EventType(models.TextChoices):
        DOMAIN = "domain", "Domain"
        INTEGRATION = "integration", "Integration"
        SYSTEM = "system", "System"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PUBLISHED = "published", "Published"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        DEAD_LETTER = "dead_letter", "Dead Letter"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    event_name = models.CharField(max_length=120, db_index=True)
    event_version = models.PositiveIntegerField(default=1)
    event_key = models.SlugField(max_length=180, unique=True, blank=True)
    source_module = models.CharField(max_length=80, db_index=True)
    event_type = models.CharField(max_length=20, choices=EventType.choices, default=EventType.INTEGRATION)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="integration_events",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="integration_events",
        null=True,
        blank=True,
    )
    aggregate_type = models.CharField(max_length=80, blank=True)
    aggregate_id = models.CharField(max_length=120, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=120, blank=True, db_index=True)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    correlation_id = models.CharField(max_length=120, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integration_events"
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(fields=["event_name", "priority", "occurred_at"], name="integration_event_priority_idx"),
            models.Index(fields=["company", "site", "occurred_at"], name="integration_event_scope_idx"),
        ]

    def save(self, *args, **kwargs):
        if not self.event_key:
            base = self.correlation_id or f"{self.source_module}-{self.event_name}-{self.aggregate_id or self.occurred_at.isoformat()}"
            self.event_key = slugify(base)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.source_module}:{self.event_name}"


class EventSubscription(models.Model):
    class ExecutionMode(models.TextChoices):
        SYNC = "sync", "Sync"
        ASYNC = "async", "Async"
        MANUAL = "manual", "Manual"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    event_name = models.CharField(max_length=120, db_index=True)
    target_module = models.CharField(max_length=80, db_index=True)
    handler_name = models.CharField(max_length=160)
    is_active = models.BooleanField(default=True)
    execution_mode = models.CharField(max_length=10, choices=ExecutionMode.choices, default=ExecutionMode.ASYNC)
    retry_policy = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integration_event_subscriptions"
        ordering = ["event_name", "target_module", "handler_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["event_name", "target_module", "handler_name"],
                name="uniq_integration_subscription_handler",
            )
        ]

    def __str__(self) -> str:
        return f"{self.event_name} -> {self.target_module}.{self.handler_name}"


class WorkflowDefinition(models.Model):
    class WorkflowType(models.TextChoices):
        EVENT_DRIVEN = "event_driven", "Event Driven"
        ORCHESTRATION = "orchestration", "Orchestration"
        AUTOMATION = "automation", "Automation"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    description = models.TextField(blank=True)
    trigger_event_name = models.CharField(max_length=120, db_index=True)
    workflow_type = models.CharField(max_length=20, choices=WorkflowType.choices, default=WorkflowType.EVENT_DRIVEN)
    config_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integration_workflow_definitions"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class WorkflowExecution(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    workflow_definition = models.ForeignKey(
        "integration_bus.WorkflowDefinition",
        on_delete=models.CASCADE,
        related_name="executions",
    )
    integration_event = models.ForeignKey(
        "integration_bus.IntegrationEvent",
        on_delete=models.CASCADE,
        related_name="workflow_executions",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    output_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integration_workflow_executions"
        ordering = ["-started_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.workflow_definition} [{self.status}]"


class AutomationTask(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SCHEDULED = "scheduled", "Scheduled"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class TaskType(models.TextChoices):
        WORKFLOW = "workflow", "Workflow"
        NOTIFICATION = "notification", "Notification"
        SNAPSHOT = "snapshot", "Snapshot"
        METRIC = "metric", "Metric"
        SYNC = "sync", "Sync"
        CUSTOM = "custom", "Custom"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    task_name = models.CharField(max_length=160)
    task_type = models.CharField(max_length=20, choices=TaskType.choices, default=TaskType.CUSTOM)
    source_module = models.CharField(max_length=80, db_index=True)
    target_module = models.CharField(max_length=80, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    correlation_id = models.CharField(max_length=120, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integration_automation_tasks"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.task_name


class IntegrationLog(models.Model):
    class LogLevel(models.TextChoices):
        DEBUG = "debug", "Debug"
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        CRITICAL = "critical", "Critical"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    source_module = models.CharField(max_length=80, db_index=True)
    target_module = models.CharField(max_length=80, blank=True)
    event_name = models.CharField(max_length=120, blank=True)
    task_name = models.CharField(max_length=160, blank=True)
    log_level = models.CharField(max_length=20, choices=LogLevel.choices, default=LogLevel.INFO)
    message = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integration_logs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.log_level}: {self.message[:60]}"


class DeadLetterEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    original_event_name = models.CharField(max_length=120, db_index=True)
    source_module = models.CharField(max_length=80, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField()
    retry_count = models.PositiveIntegerField(default=0)
    moved_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integration_dead_letter_events"
        ordering = ["-moved_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.original_event_name} -> dead_letter"


class EventDelivery(models.Model):
    class DeliveryStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"
        RETRYING = "retrying", "Retrying"
        SKIPPED = "skipped", "Skipped"
        DEAD_LETTER = "dead_letter", "Dead Letter"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    integration_event = models.ForeignKey(
        "integration_bus.IntegrationEvent",
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    subscription = models.ForeignKey(
        "integration_bus.EventSubscription",
        on_delete=models.SET_NULL,
        related_name="deliveries",
        null=True,
        blank=True,
    )
    subscriber_name = models.CharField(max_length=160, db_index=True)
    delivery_status = models.CharField(max_length=20, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING, db_index=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    delivery_payload = models.JSONField(default=dict, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integration_event_deliveries"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["integration_event", "subscriber_name"], name="uniq_integration_event_delivery"),
        ]

    def __str__(self) -> str:
        return f"{self.integration_event.event_name} -> {self.subscriber_name} [{self.delivery_status}]"


class ReactiveTriggerLog(models.Model):
    class TriggerType(models.TextChoices):
        EVENT_TO_AGENT_TRIGGER = "event_to_agent_trigger", "Event To Agent Trigger"
        EVENT_TO_BRIEFING_REFRESH = "event_to_briefing_refresh", "Event To Briefing Refresh"
        EVENT_TO_DASHBOARD_UPDATE = "event_to_dashboard_update", "Event To Dashboard Update"
        EVENT_TO_AUTONOMY_CANDIDATE = "event_to_autonomy_candidate", "Event To Autonomy Candidate"
        EVENT_TO_NOTIFICATION_CANDIDATE = "event_to_notification_candidate", "Event To Notification Candidate"
        EVENT_TO_COPILOT_REFRESH = "event_to_copilot_refresh", "Event To Copilot Refresh"

    class TriggerStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        FIRED = "fired", "Fired"
        SKIPPED = "skipped", "Skipped"
        FAILED = "failed", "Failed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    integration_event = models.ForeignKey(
        "integration_bus.IntegrationEvent",
        on_delete=models.CASCADE,
        related_name="reactive_triggers",
    )
    target_component = models.CharField(max_length=120, db_index=True)
    trigger_type = models.CharField(max_length=40, choices=TriggerType.choices, db_index=True)
    trigger_status = models.CharField(max_length=20, choices=TriggerStatus.choices, default=TriggerStatus.PENDING, db_index=True)
    summary = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integration_reactive_trigger_logs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.integration_event.event_name} -> {self.target_component} [{self.trigger_status}]"
