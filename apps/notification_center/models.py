import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class NotificationChannel(models.Model):
    class ChannelType(models.TextChoices):
        IN_APP = "in_app", "In App"
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        WHATSAPP = "whatsapp", "WhatsApp"
        WEBHOOK = "webhook", "Webhook"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    channel_type = models.CharField(max_length=20, choices=ChannelType.choices, default=ChannelType.IN_APP)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    config_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_channels"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class NotificationTemplate(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    channel = models.ForeignKey("notification_center.NotificationChannel", on_delete=models.PROTECT, related_name="templates")
    template_key = models.CharField(max_length=120, unique=True)
    subject_template = models.CharField(max_length=255, blank=True)
    body_template = models.TextField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_templates"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class NotificationPreference(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="notification_preferences",
        null=True,
        blank=True,
    )
    event_key = models.CharField(max_length=120, db_index=True)
    channel = models.ForeignKey("notification_center.NotificationChannel", on_delete=models.CASCADE, related_name="preferences")
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_preferences"
        ordering = ["event_key", "channel__name"]
        constraints = [
            models.UniqueConstraint(fields=["user", "event_key", "channel"], name="uniq_user_event_channel_preference"),
            models.UniqueConstraint(fields=["company", "event_key", "channel"], name="uniq_company_event_channel_preference"),
        ]

    def __str__(self) -> str:
        target = self.user or self.company
        return f"{target} - {self.event_key} - {self.channel}"


class NotificationEvent(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    event_key = models.CharField(max_length=120, db_index=True)
    source_module = models.CharField(max_length=80, db_index=True)
    entity_type = models.CharField(max_length=80, blank=True)
    entity_id = models.CharField(max_length=120, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_events"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.source_module}:{self.event_key}"


class NotificationMessage(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SCHEDULED = "scheduled", "Scheduled"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    event_key = models.CharField(max_length=120, db_index=True)
    channel = models.ForeignKey("notification_center.NotificationChannel", on_delete=models.PROTECT, related_name="messages")
    template = models.ForeignKey(
        "notification_center.NotificationTemplate",
        on_delete=models.SET_NULL,
        related_name="messages",
        null=True,
        blank=True,
    )
    recipient_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="notification_messages",
        null=True,
        blank=True,
    )
    recipient_company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="notification_messages",
        null=True,
        blank=True,
    )
    recipient_address = models.CharField(max_length=255, blank=True)
    subject_rendered = models.CharField(max_length=255, blank=True)
    body_rendered = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_messages"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.event_key} - {self.channel}"


class InAppNotification(models.Model):
    class NotificationType(models.TextChoices):
        INFO = "info", "Info"
        SUCCESS = "success", "Success"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        ACTION_REQUIRED = "action_required", "Action Required"

    class Status(models.TextChoices):
        UNREAD = "unread", "Unread"
        READ = "read", "Read"
        ARCHIVED = "archived", "Archived"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="in_app_notifications")
    title = models.CharField(max_length=180)
    body = models.TextField()
    link_url = models.CharField(max_length=255, blank=True)
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices, default=NotificationType.INFO)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNREAD)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_in_app_notifications"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class NotificationDeliveryLog(models.Model):
    class DeliveryStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"
        BOUNCED = "bounced", "Bounced"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    notification_message = models.ForeignKey(
        "notification_center.NotificationMessage",
        on_delete=models.CASCADE,
        related_name="delivery_logs",
    )
    channel = models.ForeignKey("notification_center.NotificationChannel", on_delete=models.PROTECT, related_name="delivery_logs")
    provider_name = models.CharField(max_length=80, blank=True)
    provider_reference = models.CharField(max_length=120, blank=True)
    delivery_status = models.CharField(max_length=20, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING)
    response_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_delivery_logs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.notification_message} - {self.delivery_status}"


class NotificationBatch(models.Model):
    class BatchType(models.TextChoices):
        OPERATIONAL = "operational", "Operational"
        CAMPAIGN = "campaign", "Campaign"
        SYSTEM = "system", "System"
        MASS = "mass", "Mass"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PROCESSING = "processing", "Processing"
        SENT = "sent", "Sent"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    batch_name = models.CharField(max_length=160)
    batch_type = models.CharField(max_length=20, choices=BatchType.choices, default=BatchType.OPERATIONAL)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_batches"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.batch_name


class NotificationBatchItem(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    batch = models.ForeignKey("notification_center.NotificationBatch", on_delete=models.CASCADE, related_name="items")
    notification_message = models.ForeignKey(
        "notification_center.NotificationMessage",
        on_delete=models.CASCADE,
        related_name="batch_items",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_batch_items"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["batch", "notification_message"], name="uniq_notification_batch_message"),
        ]

    def __str__(self) -> str:
        return f"{self.batch} - {self.notification_message}"

