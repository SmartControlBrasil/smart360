import factory
from django.utils import timezone
from datetime import timedelta

from apps.identity.models import CompanyInvitation, PasswordResetRequest, UserSession
from tests.factories.core import CompanyFactory, RoleFactory, UserFactory


class UserSessionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserSession

    user = factory.SubFactory(UserFactory)
    session_key = factory.Sequence(lambda n: f"session-{n}")
    token_identifier = factory.Sequence(lambda n: f"token-{n}")
    device_label = "Pytest Device"
    ip_address = "127.0.0.1"
    user_agent = "pytest-client"
    is_active = True
    last_seen_at = factory.LazyFunction(timezone.now)


class PasswordResetRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PasswordResetRequest

    user = factory.SubFactory(UserFactory)
    email_snapshot = factory.SelfAttribute("user.email")
    status = PasswordResetRequest.Status.PENDING
    requested_at = factory.LazyFunction(timezone.now)
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=24))
    ip_address = "127.0.0.1"


class CompanyInvitationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CompanyInvitation

    company = factory.SubFactory(CompanyFactory)
    invited_email = factory.Sequence(lambda n: f"invite{n}@smart360.local")
    invited_role = factory.SubFactory(RoleFactory)
    invited_by = factory.SubFactory(UserFactory)
    status = CompanyInvitation.Status.PENDING
    message = factory.Faker("sentence")
