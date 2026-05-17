from decimal import Decimal

import factory
from django.utils import timezone

from apps.marketplace_technicians.models import (
    ServiceRegion,
    TechnicianAssignment,
    TechnicianAvailability,
    TechnicianMatchingRecord,
    TechnicianProfile,
    TechnicianServiceOffer,
    TechnicianServiceRegion,
    TechnicianServiceRequest,
    TechnicianSkill,
    TechnicianSkillAssignment,
)
from tests.factories.core import CompanyFactory, UserFactory
from tests.factories.smart_system import AssetFactory, MaintenanceClientFactory, OperationalSiteFactory, ServiceOrderFactory


class TechnicianProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TechnicianProfile

    user = factory.SubFactory(UserFactory)
    display_name = factory.LazyAttribute(lambda obj: obj.user.display_name)
    phone = factory.LazyAttribute(lambda obj: obj.user.phone_number)
    whatsapp = factory.LazyAttribute(lambda obj: obj.user.phone_number)
    email = factory.LazyAttribute(lambda obj: obj.user.email)
    bio = factory.Faker("sentence")
    profile_type = TechnicianProfile.ProfileType.INTERNAL
    experience_years = 5
    verification_status = TechnicianProfile.VerificationStatus.APPROVED
    marketplace_status = TechnicianProfile.MarketplaceStatus.AVAILABLE
    rating_average = Decimal("4.70")
    completed_jobs_count = 10
    is_active = True
    company = factory.SubFactory(CompanyFactory)


class TechnicianSkillFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TechnicianSkill

    name = factory.Sequence(lambda n: f"Technician Skill {n}")
    description = factory.Faker("sentence")
    is_active = True


class TechnicianSkillAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TechnicianSkillAssignment

    technician_profile = factory.SubFactory(TechnicianProfileFactory)
    skill = factory.SubFactory(TechnicianSkillFactory)
    proficiency_level = TechnicianSkillAssignment.ProficiencyLevel.SPECIALIST
    years_experience = 5
    notes = factory.Faker("sentence")


class ServiceRegionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ServiceRegion

    name = factory.Sequence(lambda n: f"Regiao {n}")
    state = "SP"
    city = "Sao Paulo"
    region_type = ServiceRegion.RegionType.CITY
    is_active = True


class TechnicianServiceRegionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TechnicianServiceRegion

    technician_profile = factory.SubFactory(TechnicianProfileFactory)
    service_region = factory.SubFactory(ServiceRegionFactory)
    coverage_type = TechnicianServiceRegion.CoverageType.LOCAL


class TechnicianAvailabilityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TechnicianAvailability

    technician_profile = factory.SubFactory(TechnicianProfileFactory)
    weekday = factory.LazyFunction(lambda: timezone.localdate().isoweekday())
    start_time = timezone.datetime.strptime("08:00", "%H:%M").time()
    end_time = timezone.datetime.strptime("18:00", "%H:%M").time()
    is_available = True
    notes = factory.Faker("sentence")


class TechnicianServiceRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TechnicianServiceRequest

    requester_user = factory.SubFactory(UserFactory)
    requester_company = factory.SubFactory(CompanyFactory)
    title = factory.Sequence(lambda n: f"Technician Request {n}")
    description = factory.Faker("sentence")
    service_type = TechnicianServiceRequest.ServiceType.MAINTENANCE
    priority = TechnicianServiceRequest.Priority.MEDIUM
    requested_date = factory.LazyFunction(timezone.now)
    city = "Sao Paulo"
    state = "SP"
    address_line = "Rua Demo, 100"
    status = TechnicianServiceRequest.Status.OPEN
    related_client = factory.SubFactory(MaintenanceClientFactory)
    related_site = factory.SubFactory(OperationalSiteFactory, maintenance_client=factory.SelfAttribute("..related_client"))
    related_asset = factory.SubFactory(AssetFactory, operational_site=factory.SelfAttribute("..related_site"))
    related_service_order = factory.SubFactory(ServiceOrderFactory, client=factory.SelfAttribute("..related_client"), operational_site=factory.SelfAttribute("..related_site"), asset=factory.SelfAttribute("..related_asset"))
    notes = factory.Faker("sentence")


class TechnicianServiceOfferFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TechnicianServiceOffer

    service_request = factory.SubFactory(TechnicianServiceRequestFactory)
    technician_profile = factory.SubFactory(TechnicianProfileFactory)
    proposed_amount = Decimal("450.00")
    message = factory.Faker("sentence")
    estimated_hours = 4
    status = TechnicianServiceOffer.Status.PENDING


class TechnicianMatchingRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TechnicianMatchingRecord

    technician_service_request = factory.SubFactory(TechnicianServiceRequestFactory)
    technician_profile = factory.SubFactory(TechnicianProfileFactory)
    match_score = Decimal("88.00")
    score_specialty = Decimal("90.00")
    score_distance = Decimal("85.00")
    score_rating = Decimal("80.00")
    score_experience = Decimal("84.00")
    score_availability = Decimal("78.00")
    score_response_time = Decimal("70.00")
    distance_km = Decimal("12.00")
    ranking_position = factory.Sequence(lambda n: n + 1)
    scoring_version = "v1"
    match_reason = factory.Faker("sentence")
    calculation_context = factory.LazyFunction(dict)
    status = TechnicianMatchingRecord.Status.SUGGESTED


class TechnicianAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TechnicianAssignment

    technician_service_request = factory.SubFactory(TechnicianServiceRequestFactory)
    technician_profile = factory.SubFactory(TechnicianProfileFactory)
    assignment_status = TechnicianAssignment.AssignmentStatus.ASSIGNED
    assigned_at = factory.LazyFunction(timezone.now)
    notes = factory.Faker("sentence")
