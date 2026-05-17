import secrets

from django.contrib.auth import authenticate, password_validation
from django.db import transaction
from django.utils import timezone

from apps.audit.services.audit_service import AuditService
from apps.companies.models import Membership
from apps.notification_center.models import NotificationChannel, NotificationTemplate
from apps.notification_center.services.notification_service import (
    NotificationEventService,
    NotificationMessageService,
)
from apps.observability_center.models import SystemEventLog
from apps.observability_center.services.observability_service import MetricCounterService, SystemEventService
from apps.users.models import User

from ..models import (
    AuthEventLog,
    CompanyInvitation,
    EmailVerificationRequest,
    OnboardingProfile,
    PasswordResetRequest,
    UserSession,
)


class RequestContextService:
    @staticmethod
    def get_ip_address(request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    @staticmethod
    def get_user_agent(request):
        return request.META.get("HTTP_USER_AGENT", "")


class AuthEventService:
    @staticmethod
    def log(*, event_type, user=None, request=None, success=True, metadata=None):
        ip_address = RequestContextService.get_ip_address(request) if request else ""
        user_agent = RequestContextService.get_user_agent(request) if request else ""
        event = AuthEventLog.objects.create(
            user=user,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            metadata=metadata or {},
        )
        AuditService.log(
            action=f"identity.{event_type}",
            entity="auth_event",
            entity_id=str(event.public_id),
            user=user,
            payload={"success": success, **(metadata or {})},
        )
        if event_type in {
            AuthEventLog.EventType.LOGIN_SUCCEEDED,
            AuthEventLog.EventType.LOGIN_FAILED,
        }:
            metric_key = (
                "auth.login_success_count"
                if event_type == AuthEventLog.EventType.LOGIN_SUCCEEDED and success
                else "auth.login_failure_count"
            )
            MetricCounterService.increment_metric(metric_key=metric_key, source_module="identity")
        SystemEventService.log_system_event(
            event_type=f"auth.{event_type}",
            source_module="identity",
            severity=SystemEventLog.Severity.INFO if success else SystemEventLog.Severity.WARNING,
            entity_type="user" if user else "anonymous",
            entity_id=str(getattr(user, "public_id", "")),
            message=f"Authentication event '{event_type}' processed.",
            payload={"success": success, **(metadata or {})},
        )
        return event


class NotificationBridgeService:
    @staticmethod
    def _find_template(template_key):
        return NotificationTemplate.objects.select_related("channel").filter(template_key=template_key, is_active=True).first()

    @staticmethod
    def notify(*, event_key, template_key, recipient_user=None, recipient_company=None, recipient_address="", payload=None, fallback_channel_type="email"):
        NotificationEventService.record_event(
            event_key=event_key,
            source_module="identity",
            entity_type="user" if recipient_user else "company",
            entity_id=str(getattr(recipient_user or recipient_company, "public_id", "")),
            payload=payload or {},
        )
        template = NotificationBridgeService._find_template(template_key)
        if template:
            channel = template.channel
        else:
            channel = NotificationChannel.objects.filter(channel_type=fallback_channel_type, is_active=True).first()
        if channel is None:
            return None
        body_rendered = ""
        if template is None:
            body_rendered = (payload or {}).get("message", event_key)
        return NotificationMessageService.create_message(
            event_key=event_key,
            channel=channel,
            template=template,
            recipient_user=recipient_user,
            recipient_company=recipient_company,
            recipient_address=recipient_address,
            body_rendered=body_rendered,
            payload=payload or {},
        )


class SessionService:
    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)

    @staticmethod
    def create_session(*, user, request, device_label=""):
        token = SessionService.generate_token()
        session = UserSession.objects.create(
            user=user,
            token_identifier=token,
            device_label=device_label or request.META.get("HTTP_X_DEVICE_LABEL", "")[:120],
            ip_address=RequestContextService.get_ip_address(request),
            user_agent=RequestContextService.get_user_agent(request),
            last_seen_at=timezone.now(),
        )
        return session, token

    @staticmethod
    def rotate_session_token(*, session):
        session.token_identifier = SessionService.generate_token()
        session.last_seen_at = timezone.now()
        session.save(update_fields=["token_identifier", "last_seen_at", "updated_at"])
        return session

    @staticmethod
    def revoke_session(*, session):
        session.is_active = False
        session.revoked_at = timezone.now()
        session.save(update_fields=["is_active", "revoked_at", "updated_at"])
        return session


class IdentityAuthService:
    @staticmethod
    @transaction.atomic
    def login(*, request, email, password, device_label=""):
        user = authenticate(username=email, password=password)
        if user is None:
            AuthEventService.log(
                event_type=AuthEventLog.EventType.LOGIN_FAILED,
                request=request,
                success=False,
                metadata={"email": email},
            )
            return None, None

        user.last_login_at = timezone.now()
        user.save(update_fields=["last_login_at", "updated_at"])
        session, token = SessionService.create_session(user=user, request=request, device_label=device_label)
        AuthEventService.log(
            event_type=AuthEventLog.EventType.LOGIN_SUCCEEDED,
            user=user,
            request=request,
            success=True,
            metadata={"session_id": str(session.public_id)},
        )
        onboarding, _ = OnboardingProfile.objects.get_or_create(user=user)
        if onboarding.onboarding_status == OnboardingProfile.Status.PENDING:
            onboarding.onboarding_status = OnboardingProfile.Status.IN_PROGRESS
            onboarding.save(update_fields=["onboarding_status", "updated_at"])
        return user, token

    @staticmethod
    def logout(*, request):
        session = request.auth
        if session:
            SessionService.revoke_session(session=session)
            AuthEventService.log(
                event_type=AuthEventLog.EventType.LOGOUT,
                user=request.user,
                request=request,
                metadata={"session_id": str(session.public_id)},
            )
        return session

    @staticmethod
    def refresh_token(*, request):
        session = request.auth
        rotated = SessionService.rotate_session_token(session=session)
        AuthEventService.log(
            event_type=AuthEventLog.EventType.TOKEN_REFRESHED,
            user=request.user,
            request=request,
            metadata={"session_id": str(rotated.public_id)},
        )
        return rotated

    @staticmethod
    def change_password(*, user, current_password, new_password, request):
        if not user.check_password(current_password):
            raise ValueError("Current password is invalid.")
        password_validation.validate_password(new_password, user=user)
        user.set_password(new_password)
        user.save(update_fields=["password", "updated_at"])
        AuthEventService.log(
            event_type=AuthEventLog.EventType.PASSWORD_CHANGED,
            user=user,
            request=request,
            metadata={},
        )
        return user


class PasswordResetService:
    @staticmethod
    @transaction.atomic
    def request_reset(*, email, request):
        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            return None
        reset_request = PasswordResetRequest.objects.create(
            user=user,
            email_snapshot=user.email,
            ip_address=RequestContextService.get_ip_address(request),
        )
        AuthEventService.log(
            event_type=AuthEventLog.EventType.PASSWORD_RESET_REQUESTED,
            user=user,
            request=request,
            metadata={"reset_request_id": str(reset_request.public_id)},
        )
        NotificationBridgeService.notify(
            event_key="password_reset_requested",
            template_key="password_reset_email",
            recipient_user=user,
            recipient_address=user.email,
            payload={"token": reset_request.token, "email": user.email},
        )
        return reset_request

    @staticmethod
    @transaction.atomic
    def confirm_reset(*, token, new_password, request=None):
        reset_request = PasswordResetRequest.objects.select_related("user").filter(token=token).first()
        if reset_request is None or reset_request.status != PasswordResetRequest.Status.PENDING:
            raise ValueError("Invalid or expired reset token.")
        if reset_request.expires_at <= timezone.now():
            reset_request.status = PasswordResetRequest.Status.EXPIRED
            reset_request.save(update_fields=["status", "updated_at"])
            raise ValueError("Invalid or expired reset token.")

        password_validation.validate_password(new_password, user=reset_request.user)
        reset_request.user.set_password(new_password)
        reset_request.user.save(update_fields=["password", "updated_at"])
        reset_request.status = PasswordResetRequest.Status.USED
        reset_request.used_at = timezone.now()
        reset_request.save(update_fields=["status", "used_at", "updated_at"])
        AuthEventService.log(
            event_type=AuthEventLog.EventType.PASSWORD_RESET_COMPLETED,
            user=reset_request.user,
            request=request,
            metadata={"reset_request_id": str(reset_request.public_id)},
        )
        return reset_request


class EmailVerificationService:
    @staticmethod
    @transaction.atomic
    def request_verification(*, user, request):
        verification = EmailVerificationRequest.objects.create(
            user=user,
            email_snapshot=user.email,
        )
        AuthEventService.log(
            event_type=AuthEventLog.EventType.EMAIL_VERIFICATION_REQUESTED,
            user=user,
            request=request,
            metadata={"verification_request_id": str(verification.public_id)},
        )
        NotificationBridgeService.notify(
            event_key="email_verification_requested",
            template_key="email_verification_email",
            recipient_user=user,
            recipient_address=user.email,
            payload={"token": verification.token, "email": user.email},
        )
        return verification

    @staticmethod
    @transaction.atomic
    def confirm_verification(*, token, request=None):
        verification = EmailVerificationRequest.objects.select_related("user").filter(token=token).first()
        if verification is None or verification.status != EmailVerificationRequest.Status.PENDING:
            raise ValueError("Invalid or expired verification token.")
        if verification.expires_at <= timezone.now():
            verification.status = EmailVerificationRequest.Status.EXPIRED
            verification.save(update_fields=["status", "updated_at"])
            raise ValueError("Invalid or expired verification token.")

        verification.status = EmailVerificationRequest.Status.VERIFIED
        verification.verified_at = timezone.now()
        verification.save(update_fields=["status", "verified_at", "updated_at"])

        user = verification.user
        user.is_verified = True
        user.save(update_fields=["is_verified", "updated_at"])
        onboarding, _ = OnboardingProfile.objects.get_or_create(user=user)
        onboarding.email_verified = True
        if onboarding.profile_completed and onboarding.company_setup_completed:
            onboarding.onboarding_status = OnboardingProfile.Status.COMPLETED
            onboarding.completed_at = timezone.now()
        onboarding.save(update_fields=["email_verified", "onboarding_status", "completed_at", "updated_at"])
        AuthEventService.log(
            event_type=AuthEventLog.EventType.EMAIL_VERIFIED,
            user=user,
            request=request,
            metadata={"verification_request_id": str(verification.public_id)},
        )
        return verification


class InvitationService:
    @staticmethod
    @transaction.atomic
    def create_invitation(*, company, invited_email, invited_role, invited_by, message=""):
        invitation = CompanyInvitation.objects.create(
            company=company,
            invited_email=invited_email.lower(),
            invited_role=invited_role,
            invited_by=invited_by,
            message=message,
        )
        AuthEventService.log(
            event_type=AuthEventLog.EventType.INVITATION_CREATED,
            user=invited_by,
            metadata={"invitation_id": str(invitation.public_id), "company": company.slug},
        )
        NotificationBridgeService.notify(
            event_key="company_invitation_created",
            template_key="company_invitation_email",
            recipient_company=company,
            recipient_address=invited_email,
            payload={
                "token": invitation.token,
                "company_name": company.name,
                "invited_email": invited_email,
                "message": message,
            },
        )
        return invitation

    @staticmethod
    @transaction.atomic
    def accept_invitation(*, token, user=None, first_name="", last_name="", password="", request=None):
        invitation = CompanyInvitation.objects.select_related("company", "invited_role").filter(token=token).first()
        if invitation is None or invitation.status != CompanyInvitation.Status.PENDING:
            raise ValueError("Invalid or expired invitation.")
        if invitation.expires_at <= timezone.now():
            invitation.status = CompanyInvitation.Status.EXPIRED
            invitation.save(update_fields=["status", "updated_at"])
            raise ValueError("Invalid or expired invitation.")

        accepted_user = user or User.objects.filter(email__iexact=invitation.invited_email).first()
        if accepted_user is None:
            if not password or not first_name:
                raise ValueError("User details are required to accept invitation.")
            password_validation.validate_password(password)
            accepted_user = User.objects.create_user(
                email=invitation.invited_email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                user_type=User.UserType.PARTNER,
            )

        membership, _ = Membership.objects.get_or_create(
            user=accepted_user,
            company=invitation.company,
            defaults={
                "status": Membership.Status.ACTIVE,
                "joined_at": timezone.now(),
            },
        )
        membership.status = Membership.Status.ACTIVE
        membership.joined_at = membership.joined_at or timezone.now()
        membership.save(update_fields=["status", "joined_at", "updated_at"])
        if invitation.invited_role:
            membership.roles.add(invitation.invited_role)

        invitation.status = CompanyInvitation.Status.ACCEPTED
        invitation.accepted_at = timezone.now()
        invitation.save(update_fields=["status", "accepted_at", "updated_at"])
        onboarding, _ = OnboardingProfile.objects.get_or_create(user=accepted_user)
        onboarding.company_setup_completed = True
        onboarding.onboarding_status = OnboardingProfile.Status.IN_PROGRESS
        onboarding.save(update_fields=["company_setup_completed", "onboarding_status", "updated_at"])
        AuthEventService.log(
            event_type=AuthEventLog.EventType.INVITATION_ACCEPTED,
            user=accepted_user,
            request=request,
            metadata={"invitation_id": str(invitation.public_id), "company": invitation.company.slug},
        )
        return invitation, accepted_user
