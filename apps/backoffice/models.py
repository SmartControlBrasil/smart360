import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class BackofficeQueue(models.Model):
    class QueueType(models.TextChoices):
        REVIEW = "review", "Review"
        OPERATIONAL = "operational", "Operational"
        APPROVAL = "approval", "Approval"
        BILLING = "billing", "Billing"
        INCIDENT = "incident", "Incident"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    queue_type = models.CharField(max_length=20, choices=QueueType.choices, default=QueueType.OPERATIONAL)
    source_module = models.CharField(max_length=80, db_index=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    ordering = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "backoffice_queues"
        ordering = ["ordering", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class BackofficeQueueItem(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        REVIEWED = "reviewed", "Reviewed"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        RESOLVED = "resolved", "Resolved"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    queue = models.ForeignKey("backoffice.BackofficeQueue", on_delete=models.CASCADE, related_name="items")
    item_type = models.CharField(max_length=80)
    item_id = models.CharField(max_length=120)
    reference_label = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="backoffice_queue_items",
        null=True,
        blank=True,
    )
    due_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "backoffice_queue_items"
        ordering = ["queue__ordering", "-created_at"]

    def __str__(self) -> str:
        return self.reference_label


class BackofficeAlert(models.Model):
    class AlertType(models.TextChoices):
        OPERATIONAL = "operational", "Operational"
        SECURITY = "security", "Security"
        BILLING = "billing", "Billing"
        WORKFLOW = "workflow", "Workflow"
        REVIEW = "review", "Review"

    class Severity(models.TextChoices):
        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"
        DISMISSED = "dismissed", "Dismissed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    alert_type = models.CharField(max_length=20, choices=AlertType.choices, default=AlertType.OPERATIONAL)
    source_module = models.CharField(max_length=80, db_index=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.WARNING)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    related_item_type = models.CharField(max_length=80, blank=True)
    related_item_id = models.CharField(max_length=120, blank=True)
    summary = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "backoffice_alerts"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.title}-{self.source_module}")
        if self.status == self.Status.RESOLVED and self.resolved_at is None:
            self.resolved_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class BackofficeTask(models.Model):
    class TaskType(models.TextChoices):
        REVIEW = "review", "Review"
        APPROVAL = "approval", "Approval"
        FOLLOW_UP = "follow_up", "Follow Up"
        ESCALATION = "escalation", "Escalation"
        INTERNAL = "internal", "Internal"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        BLOCKED = "blocked", "Blocked"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=180)
    task_type = models.CharField(max_length=20, choices=TaskType.choices, default=TaskType.INTERNAL)
    source_module = models.CharField(max_length=80, db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="backoffice_tasks",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    due_at = models.DateTimeField(null=True, blank=True)
    related_item_type = models.CharField(max_length=80, blank=True)
    related_item_id = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "backoffice_tasks"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.status == self.Status.COMPLETED and self.completed_at is None:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class BackofficeQuickAction(models.Model):
    class ActionType(models.TextChoices):
        NAVIGATION = "navigation", "Navigation"
        REVIEW = "review", "Review"
        CREATE = "create", "Create"
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    target_module = models.CharField(max_length=80, db_index=True)
    action_type = models.CharField(max_length=20, choices=ActionType.choices, default=ActionType.NAVIGATION)
    label = models.CharField(max_length=120)
    route_path = models.CharField(max_length=255, blank=True)
    config_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    ordering = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "backoffice_quick_actions"
        ordering = ["ordering", "label"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.label


class BackofficeWidget(models.Model):
    class WidgetType(models.TextChoices):
        METRIC_CARD = "metric_card", "Metric Card"
        LIST = "list", "List"
        ALERT_FEED = "alert_feed", "Alert Feed"
        TASK_FEED = "task_feed", "Task Feed"
        QUEUE_SUMMARY = "queue_summary", "Queue Summary"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    widget_type = models.CharField(max_length=20, choices=WidgetType.choices, default=WidgetType.METRIC_CARD)
    source_module = models.CharField(max_length=80, db_index=True)
    title = models.CharField(max_length=180)
    config_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    ordering = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "backoffice_widgets"
        ordering = ["ordering", "title"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class BackofficeNote(models.Model):
    class NoteType(models.TextChoices):
        REVIEW = "review", "Review"
        INTERNAL = "internal", "Internal"
        APPROVAL = "approval", "Approval"
        INCIDENT = "incident", "Incident"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    note_type = models.CharField(max_length=20, choices=NoteType.choices, default=NoteType.INTERNAL)
    related_item_type = models.CharField(max_length=80)
    related_item_id = models.CharField(max_length=120)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="backoffice_notes",
        null=True,
        blank=True,
    )
    content = models.TextField()
    is_private = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "backoffice_notes"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.note_type} - {self.related_item_type}"

