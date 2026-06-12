from django.db import models


class AutomationLog(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        IGNORED = "ignored", "Ignored"

    source = models.CharField(max_length=100)
    workflow_name = models.CharField(max_length=150, blank=True)
    event_type = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payload = models.JSONField(default=dict, blank=True)
    response = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "automation_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.source}::{self.event_type} ({self.status})"


class AutomationEvent(models.Model):
    event_type = models.CharField(max_length=100)
    source = models.CharField(max_length=100)
    payload = models.JSONField(default=dict, blank=True)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "automation_events"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.source}::{self.event_type}"


class WebhookEndpoint(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    secret_token = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "automation_webhook_endpoints"
        ordering = ["name"]

    def __str__(self):
        return self.name
