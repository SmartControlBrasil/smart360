import uuid

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=120)
    entity = models.CharField(max_length=120)
    entity_id = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["entity", "entity_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.action}::{self.entity}::{self.entity_id}"
