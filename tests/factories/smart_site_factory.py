from decimal import Decimal

import factory
from django.utils import timezone

from apps.smart_site_factory.models import Niche, SiteOrder, SiteProjectIntake, Template
from tests.factories.core import CompanyFactory, UserFactory


class NicheFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Niche

    name = factory.Sequence(lambda n: f"Niche {n}")
    slug = factory.Sequence(lambda n: f"niche-{n}")
    description = factory.Faker("sentence")
    is_active = True


class TemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Template

    niche = factory.SubFactory(NicheFactory)
    name = factory.Sequence(lambda n: f"Template {n}")
    slug = factory.Sequence(lambda n: f"template-{n}")
    description = factory.Faker("sentence")
    version = "1.0.0"
    template_type = Template.TemplateType.ONE_PAGE
    base_price = Decimal("1990.00")
    status = Template.Status.READY
    is_active = True
    metadata = factory.LazyFunction(dict)


class SiteOrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SiteOrder

    company = factory.SubFactory(CompanyFactory)
    requester = factory.SubFactory(UserFactory)
    niche = factory.SubFactory(NicheFactory)
    selected_template = factory.SubFactory(TemplateFactory)
    recommended_template = factory.SelfAttribute("selected_template")
    status = SiteOrder.Status.INTAKE_PENDING
    notes = factory.Faker("sentence")
    final_price = Decimal("1990.00")
    ordered_at = factory.LazyFunction(timezone.now)
    metadata = factory.LazyFunction(dict)


class SiteProjectIntakeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SiteProjectIntake

    site_order = factory.SubFactory(SiteOrderFactory)
    company_name = factory.LazyAttribute(lambda obj: obj.site_order.company.name)
    phone = "+551140001000"
    whatsapp = "+5511999990000"
    city = "Sao Paulo"
    state = "SP"
    business_description = factory.Faker("paragraph")
    main_services = factory.LazyFunction(lambda: ["Landing page", "Formulario"])
    notes = factory.Faker("sentence")

