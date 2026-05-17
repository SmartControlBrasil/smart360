import factory
from django.utils import timezone

from apps.growth_engine.models import Lead, LeadInteraction, LeadSource
from tests.factories.core import UserFactory
from tests.factories.smart_site_factory import NicheFactory


class LeadSourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LeadSource

    name = factory.Sequence(lambda n: f"Lead Source {n}")
    source_type = LeadSource.SourceType.ORGANIC
    description = factory.Faker("sentence")
    is_active = True


class LeadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Lead

    company_name = factory.Sequence(lambda n: f"Lead Company {n}")
    contact_name = factory.Faker("name")
    email = factory.Sequence(lambda n: f"lead{n}@smart360.local")
    phone = factory.Sequence(lambda n: f"+55113000{n:04d}")
    whatsapp = factory.Sequence(lambda n: f"+55119988{n:04d}")
    city = "Sao Paulo"
    state = "SP"
    niche = factory.SubFactory(NicheFactory)
    source = factory.SubFactory(LeadSourceFactory)
    status = Lead.Status.NEW
    score = 50
    notes = factory.Faker("sentence")
    assigned_to = factory.SubFactory(UserFactory)
    created_by = factory.SubFactory(UserFactory)
    metadata = factory.LazyFunction(dict)


class LeadInteractionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LeadInteraction

    lead = factory.SubFactory(LeadFactory)
    interaction_type = LeadInteraction.InteractionType.WHATSAPP
    channel = LeadInteraction.Channel.WHATSAPP
    summary = factory.Faker("sentence")
    happened_at = factory.LazyFunction(timezone.now)
    owner = factory.SubFactory(UserFactory)

