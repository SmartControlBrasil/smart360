import secrets
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_secure_token():
    return secrets.token_urlsafe(32)


def default_password_reset_expiry():
    return timezone.now() + timedelta(hours=24)


def default_email_verification_expiry():
    return timezone.now() + timedelta(hours=24)


def default_company_invitation_expiry():
    return timezone.now() + timedelta(days=7)


class UserSession(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_sessions")
    session_key = models.CharField(max_length=120, blank=True)
    token_identifier = models.CharField(max_length=255, blank=True, unique=True)
    device_label = models.CharField(max_length=120, blank=True)
    ip_address = models.CharField(max_length=64, blank=True)
    user_agent = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "identity_user_sessions"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.device_label or self.public_id}"


class PasswordResetRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        USED = "used", "Used"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="password_reset_requests")
    email_snapshot = models.EmailField()
    token = models.CharField(max_length=255, unique=True, default=generate_secure_token)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(default=default_password_reset_expiry)
    used_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "identity_password_reset_requests"
        ordering = ["-requested_at"]

    def __str__(self) -> str:
        return f"{self.email_snapshot} - {self.status}"


class EmailVerificationRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_verification_requests")
    email_snapshot = models.EmailField()
    token = models.CharField(max_length=255, unique=True, default=generate_secure_token)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(default=default_email_verification_expiry)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "identity_email_verification_requests"
        ordering = ["-requested_at"]

    def __str__(self) -> str:
        return f"{self.email_snapshot} - {self.status}"


class CompanyInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"
        REVOKED = "revoked", "Revoked"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="invitations")
    invited_email = models.EmailField()
    invited_role = models.ForeignKey(
        "roles.Role",
        on_delete=models.SET_NULL,
        related_name="company_invitations",
        null=True,
        blank=True,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="sent_company_invitations",
        null=True,
        blank=True,
    )
    token = models.CharField(max_length=255, unique=True, default=generate_secure_token)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_company_invitation_expiry)
    accepted_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "identity_company_invitations"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.invited_email} -> {self.company.name}"


class AuthEventLog(models.Model):
    class EventType(models.TextChoices):
        LOGIN_SUCCEEDED = "login_succeeded", "Login Succeeded"
        LOGIN_FAILED = "login_failed", "Login Failed"
        LOGOUT = "logout", "Logout"
        TOKEN_REFRESHED = "token_refreshed", "Token Refreshed"
        PASSWORD_CHANGED = "password_changed", "Password Changed"
        PASSWORD_RESET_REQUESTED = "password_reset_requested", "Password Reset Requested"
        PASSWORD_RESET_COMPLETED = "password_reset_completed", "Password Reset Completed"
        EMAIL_VERIFICATION_REQUESTED = "email_verification_requested", "Email Verification Requested"
        EMAIL_VERIFIED = "email_verified", "Email Verified"
        INVITATION_CREATED = "invitation_created", "Invitation Created"
        INVITATION_ACCEPTED = "invitation_accepted", "Invitation Accepted"
        SESSION_REVOKED = "session_revoked", "Session Revoked"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="auth_event_logs",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices, db_index=True)
    ip_address = models.CharField(max_length=64, blank=True)
    user_agent = models.TextField(blank=True)
    success = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "identity_auth_event_logs"
        ordering = ["-occurred_at", "-created_at"]

    def __str__(self) -> str:
        return self.event_type


class OnboardingProfile(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        SKIPPED = "skipped", "Skipped"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="onboarding_profile")
    onboarding_status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    current_step = models.CharField(max_length=80, default="profile")
    profile_completed = models.BooleanField(default=False)
    company_setup_completed = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    accepted_terms_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "identity_onboarding_profiles"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.onboarding_status}"
