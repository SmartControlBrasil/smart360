from decimal import Decimal

import factory
from django.utils import timezone

from apps.analytics_platform.models import AnalyticsEvent, AnalyticsMetric, AnalyticsMetricValue
from tests.factories.core import CompanyFactory, UserFactory


class AnalyticsEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AnalyticsEvent

    event_type = "service_order_created"
    source_module = "smart_system"
    entity_type = "service_order"
    entity_id = factory.Sequence(lambda n: str(n + 1))
    user = factory.SubFactory(UserFactory)
    company = factory.SubFactory(CompanyFactory)
    payload = factory.LazyFunction(dict)
    occurred_at = factory.LazyFunction(timezone.now)


class AnalyticsMetricFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AnalyticsMetric

    metric_name = factory.Sequence(lambda n: f"metric_{n}")
    metric_type = AnalyticsMetric.MetricType.COUNTER
    description = factory.Faker("sentence")
    unit = "count"
    is_active = True


class AnalyticsMetricValueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AnalyticsMetricValue

    metric = factory.SubFactory(AnalyticsMetricFactory)
    value = Decimal("10.00")
    calculated_at = factory.LazyFunction(timezone.now)
    reference_date = factory.LazyFunction(lambda: timezone.now().date())
    source_module = "smart_system"

