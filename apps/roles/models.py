import uuid

from django.db import models


class Role(models.Model):
    class Scope(models.TextChoices):
        PLATFORM = "platform", "Platform"
        COMPANY = "company", "Company"
        TEAM = "team", "Team"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    code = models.CharField(max_length=60, unique=True)
    label = models.CharField(max_length=120)
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.COMPANY)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "roles"
        ordering = ["scope", "label"]

    def __str__(self) -> str:
        return f"{self.label} [{self.code}]"
