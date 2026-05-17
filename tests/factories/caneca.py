import factory
from django.core.files.base import ContentFile

from apps.caneca_de_garagem.models import CreativeStoreProfile, CustomizationRequest, ProductionJob
from tests.factories.core import UserFactory
from tests.factories.market_core import MarketplaceOrderItemFactory, MarketplaceOrderFactory, MarketplaceProductFactory, MarketplaceVendorFactory


class CreativeStoreProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CreativeStoreProfile

    vendor = factory.SubFactory(MarketplaceVendorFactory)
    display_name = factory.Sequence(lambda n: f"Creative Store {n}")
    bio = factory.Faker("sentence")
    profile_type = CreativeStoreProfile.ProfileType.MIXED
    production_capabilities = factory.LazyFunction(lambda: ["sublimation", "print"])
    is_internal_factory = False
    lead_time_days = 3


class CustomizationRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CustomizationRequest

    order_item = factory.SubFactory(MarketplaceOrderItemFactory)
    customer_text = factory.LazyFunction(lambda: {"name": "Cliente Demo"})
    uploaded_assets = factory.LazyFunction(list)
    font_choice = "Poppins"
    color_choice = "black"
    extra_notes = factory.Faker("sentence")
    approval_status = CustomizationRequest.ApprovalStatus.PENDING


class ProductionJobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductionJob

    order = factory.SubFactory(MarketplaceOrderFactory)
    order_item = factory.SubFactory(MarketplaceOrderItemFactory)
    vendor = factory.SubFactory(MarketplaceVendorFactory)
    internal_factory = factory.SubFactory(CreativeStoreProfileFactory)
    job_type = ProductionJob.JobType.ART_PREP
    status = ProductionJob.Status.QUEUED
    queue_position = 1
    assigned_to = factory.SubFactory(UserFactory)
    notes = factory.Faker("sentence")

