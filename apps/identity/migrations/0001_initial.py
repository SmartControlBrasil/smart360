import django.db.models.deletion
import django.utils.timezone
import uuid

from django.conf import settings
from django.db import migrations, models

import apps.identity.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0001_initial"),
        ("roles", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuthEventLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("login_succeeded", "Login Succeeded"),
                            ("login_failed", "Login Failed"),
                            ("logout", "Logout"),
                            ("token_refreshed", "Token Refreshed"),
                            ("password_changed", "Password Changed"),
                            ("password_reset_requested", "Password Reset Requested"),
                            ("password_reset_completed", "Password Reset Completed"),
                            ("email_verification_requested", "Email Verification Requested"),
                            ("email_verified", "Email Verified"),
                            ("invitation_created", "Invitation Created"),
                            ("invitation_accepted", "Invitation Accepted"),
                            ("session_revoked", "Session Revoked"),
                        ],
                        db_index=True,
                        max_length=40,
                    ),
                ),
                ("ip_address", models.CharField(blank=True, max_length=64)),
                ("user_agent", models.TextField(blank=True)),
                ("success", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="auth_event_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "identity_auth_event_logs", "ordering": ["-occurred_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="EmailVerificationRequest",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("email_snapshot", models.EmailField(max_length=254)),
                ("token", models.CharField(default=apps.identity.models.generate_secure_token, max_length=255, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("verified", "Verified"),
                            ("expired", "Expired"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("requested_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField(default=apps.identity.models.default_email_verification_expiry)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="email_verification_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "identity_email_verification_requests", "ordering": ["-requested_at"]},
        ),
        migrations.CreateModel(
            name="OnboardingProfile",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "onboarding_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("in_progress", "In Progress"),
                            ("completed", "Completed"),
                            ("skipped", "Skipped"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("current_step", models.CharField(default="profile", max_length=80)),
                ("profile_completed", models.BooleanField(default=False)),
                ("company_setup_completed", models.BooleanField(default=False)),
                ("email_verified", models.BooleanField(default=False)),
                ("accepted_terms_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="onboarding_profile", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"db_table": "identity_onboarding_profiles", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="PasswordResetRequest",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("email_snapshot", models.EmailField(max_length=254)),
                ("token", models.CharField(default=apps.identity.models.generate_secure_token, max_length=255, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("used", "Used"),
                            ("expired", "Expired"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("requested_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField(default=apps.identity.models.default_password_reset_expiry)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("ip_address", models.CharField(blank=True, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="password_reset_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "identity_password_reset_requests", "ordering": ["-requested_at"]},
        ),
        migrations.CreateModel(
            name="UserSession",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("session_key", models.CharField(blank=True, max_length=120)),
                ("token_identifier", models.CharField(blank=True, max_length=255, unique=True)),
                ("device_label", models.CharField(blank=True, max_length=120)),
                ("ip_address", models.CharField(blank=True, max_length=64)),
                ("user_agent", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_sessions", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"db_table": "identity_user_sessions", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="CompanyInvitation",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("invited_email", models.EmailField(max_length=254)),
                ("token", models.CharField(default=apps.identity.models.generate_secure_token, max_length=255, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("accepted", "Accepted"),
                            ("expired", "Expired"),
                            ("cancelled", "Cancelled"),
                            ("revoked", "Revoked"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField(default=apps.identity.models.default_company_invitation_expiry)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="invitations", to="companies.company"),
                ),
                (
                    "invited_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sent_company_invitations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "invited_role",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="company_invitations",
                        to="roles.role",
                    ),
                ),
            ],
            options={"db_table": "identity_company_invitations", "ordering": ["-created_at"]},
        ),
    ]
