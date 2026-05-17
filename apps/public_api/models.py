import secrets
import uuid

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class IntegrationCredential(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=140)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="integration_credentials",
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="integration_credentials",
    )
    key_prefix = models.CharField(max_length=24, unique=True, editable=False)
    secret_hash = models.CharField(max_length=255, blank=True)
    allowed_scopes = models.JSONField(default=list, blank=True)
    allowed_ips = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_integration_credentials",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "public_api_integration_credentials"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    @staticmethod
    def generate_token_parts():
        return secrets.token_hex(6), secrets.token_urlsafe(24)

    def set_token(self, raw_secret: str):
        self.secret_hash = make_password(raw_secret)

    def check_token(self, raw_secret: str) -> bool:
        return check_password(raw_secret, self.secret_hash)

    def issue_token(self) -> str:
        prefix, secret = self.generate_token_parts()
        self.key_prefix = prefix
        self.set_token(secret)
        return f"{prefix}.{secret}"

    @property
    def is_current(self) -> bool:
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at <= timezone.now():
            return False
        return True

