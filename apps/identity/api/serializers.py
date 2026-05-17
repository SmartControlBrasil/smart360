from django.utils import timezone
from rest_framework import serializers

from apps.companies.models import Membership
from apps.users.api.serializers import UserSerializer

from ..models import (
    AuthEventLog,
    CompanyInvitation,
    OnboardingProfile,
    UserSession,
)


class AuthLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    device_label = serializers.CharField(required=False, allow_blank=True, max_length=120)


class AuthTokenResponseSerializer(serializers.Serializer):
    """Resposta padrao de autenticacao com token de sessao."""

    token = serializers.CharField(read_only=True)
    user = UserSerializer(read_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        return attrs


class EmailVerificationRequestSerializer(serializers.Serializer):
    pass


class EmailVerificationConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = (
            "id",
            "public_id",
            "session_key",
            "device_label",
            "ip_address",
            "user_agent",
            "is_active",
            "last_seen_at",
            "created_at",
            "revoked_at",
        )
        read_only_fields = fields


class CompanyInvitationSerializer(serializers.ModelSerializer):
    invited_role_label = serializers.CharField(source="invited_role.label", read_only=True)

    class Meta:
        model = CompanyInvitation
        fields = (
            "id",
            "public_id",
            "company",
            "invited_email",
            "invited_role",
            "invited_role_label",
            "invited_by",
            "token",
            "status",
            "message",
            "created_at",
            "expires_at",
            "accepted_at",
        )
        read_only_fields = ("id", "public_id", "invited_by", "token", "status", "created_at", "accepted_at")


class CompanyInvitationAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, allow_blank=True, write_only=True)


class AuthEventLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthEventLog
        fields = ("id", "public_id", "user", "event_type", "ip_address", "user_agent", "success", "metadata", "occurred_at", "created_at")
        read_only_fields = fields


class OnboardingProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = OnboardingProfile
        fields = (
            "id",
            "public_id",
            "onboarding_status",
            "current_step",
            "profile_completed",
            "company_setup_completed",
            "email_verified",
            "accepted_terms_at",
            "completed_at",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "email_verified", "completed_at", "created_at", "updated_at")

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        if instance.profile_completed and instance.company_setup_completed and instance.email_verified:
            instance.onboarding_status = OnboardingProfile.Status.COMPLETED
            instance.completed_at = instance.completed_at or timezone.now()
            instance.save(update_fields=["onboarding_status", "completed_at", "updated_at"])
        return instance


class MembershipSerializer(serializers.ModelSerializer):
    role_codes = serializers.SlugRelatedField(source="roles", slug_field="code", many=True, read_only=True)

    class Meta:
        model = Membership
        fields = ("public_id", "company", "status", "is_primary", "joined_at", "role_codes")
        read_only_fields = fields
