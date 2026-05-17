import factory
from django.utils import timezone

from apps.marketplace_analytical.models import (
    AnalyticalAssignment,
    AnalyticalProvider,
    AnalyticalRequest,
    AnalyticalServiceCategory,
)
from tests.factories.core import CompanyFactory, UserFactory
from tests.factories.smart_system import AssetFactory, OperationalSiteFactory, ServiceOrderFactory


class AnalyticalProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AnalyticalProvider

    company = factory.SubFactory(CompanyFactory)
    user = factory.SubFactory(UserFactory)
    display_name = factory.Sequence(lambda n: f"Analytical Provider {n}")
    contact_email = factory.Sequence(lambda n: f"provider{n}@smart360.local")
    contact_phone = factory.Sequence(lambda n: f"+55115000{n:04d}")
    description = factory.Faker("sentence")
    provider_type = AnalyticalProvider.ProviderType.COMPANY
    verification_status = AnalyticalProvider.VerificationStatus.APPROVED
    marketplace_status = AnalyticalProvider.MarketplaceStatus.ACTIVE
    is_active = True


class AnalyticalServiceCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AnalyticalServiceCategory

    name = factory.Sequence(lambda n: f"Analytical Category {n}")
    description = factory.Faker("sentence")
    is_active = True


class AnalyticalRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AnalyticalRequest

    requester_user = factory.SubFactory(UserFactory)
    requester_company = factory.SubFactory(CompanyFactory)
    title = factory.Sequence(lambda n: f"Analytical Request {n}")
    description = factory.Faker("sentence")
    category = factory.SubFactory(AnalyticalServiceCategoryFactory)
    priority = AnalyticalRequest.Priority.MEDIUM
    related_asset = factory.SubFactory(AssetFactory)
    related_site = factory.SubFactory(OperationalSiteFactory)
    related_service_order = factory.SubFactory(ServiceOrderFactory)
    city = "Sao Paulo"
    state = "SP"
    country = "BR"
    requested_date = factory.LazyFunction(timezone.now)
    status = AnalyticalRequest.Status.OPEN
    notes = factory.Faker("sentence")


class AnalyticalAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AnalyticalAssignment

    analytical_request = factory.SubFactory(AnalyticalRequestFactory)
    provider = factory.SubFactory(AnalyticalProviderFactory)
    status = AnalyticalAssignment.Status.ASSIGNED
    assigned_at = factory.LazyFunction(timezone.now)
    notes = factory.Faker("sentence")

