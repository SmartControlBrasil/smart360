from django.contrib import admin

from .models import (
    AuthEventLog,
    CompanyInvitation,
    EmailVerificationRequest,
    OnboardingProfile,
    PasswordResetRequest,
    UserSession,
)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "device_label", "ip_address", "is_active", "last_seen_at", "created_at", "revoked_at")
    list_filter = ("is_active", "created_at", "revoked_at")
    search_fields = ("user__email", "device_label", "ip_address", "user_agent", "token_identifier")
    readonly_fields = ("public_id", "token_identifier", "last_seen_at", "created_at", "revoked_at", "updated_at")
    autocomplete_fields = ("user",)


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "email_snapshot", "status", "requested_at", "expires_at", "used_at")
    list_filter = ("status", "requested_at", "expires_at")
    search_fields = ("user__email", "email_snapshot", "token", "ip_address")
    readonly_fields = ("public_id", "token", "requested_at", "expires_at", "used_at", "created_at", "updated_at")
    autocomplete_fields = ("user",)


@admin.register(EmailVerificationRequest)
class EmailVerificationRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "email_snapshot", "status", "requested_at", "expires_at", "verified_at")
    list_filter = ("status", "requested_at", "expires_at")
    search_fields = ("user__email", "email_snapshot", "token")
    readonly_fields = ("public_id", "token", "requested_at", "expires_at", "verified_at", "created_at", "updated_at")
    autocomplete_fields = ("user",)


@admin.register(CompanyInvitation)
class CompanyInvitationAdmin(admin.ModelAdmin):
    list_display = ("company", "invited_email", "invited_role", "status", "created_at", "expires_at", "accepted_at")
    list_filter = ("status", "company", "invited_role")
    search_fields = ("company__name", "invited_email", "token", "message")
    readonly_fields = ("public_id", "token", "created_at", "accepted_at", "updated_at")
    autocomplete_fields = ("company", "invited_role", "invited_by")


@admin.register(AuthEventLog)
class AuthEventLogAdmin(admin.ModelAdmin):
    list_display = ("user", "event_type", "success", "ip_address", "occurred_at")
    list_filter = ("event_type", "success", "occurred_at")
    search_fields = ("user__email", "ip_address", "user_agent")
    readonly_fields = ("public_id", "occurred_at", "created_at")
    autocomplete_fields = ("user",)


@admin.register(OnboardingProfile)
class OnboardingProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "onboarding_status", "current_step", "profile_completed", "company_setup_completed", "email_verified")
    list_filter = ("onboarding_status", "profile_completed", "company_setup_completed", "email_verified")
    search_fields = ("user__email", "current_step")
    readonly_fields = ("public_id", "completed_at", "created_at", "updated_at")
    autocomplete_fields = ("user",)

