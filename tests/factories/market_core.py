from decimal import Decimal

import factory
from django.utils import timezone

from apps.market_core.models import MarketplaceOrder, MarketplaceOrderItem, MarketplaceProduct, MarketplaceVendor
from tests.factories.core import CompanyFactory, UserFactory


class MarketplaceVendorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MarketplaceVendor

    company = factory.SubFactory(CompanyFactory)
    owner = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Vendor {n}")
    slug = factory.Sequence(lambda n: f"vendor-{n}")
    status = MarketplaceVendor.Status.ACTIVE
    accepts_internal_production = False
    metadata = factory.LazyFunction(dict)


class MarketplaceProductFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MarketplaceProduct

    vendor = factory.SubFactory(MarketplaceVendorFactory)
    name = factory.Sequence(lambda n: f"Product {n}")
    slug = factory.Sequence(lambda n: f"product-{n}")
    sku = factory.Sequence(lambda n: f"SKU-{n:05d}")
    description = factory.Faker("sentence")
    base_price = Decimal("99.90")
    is_customizable = True
    is_active = True
    metadata = factory.LazyFunction(dict)


class MarketplaceOrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MarketplaceOrder

    code = factory.Sequence(lambda n: f"ORD-{n:05d}")
    customer = factory.SubFactory(UserFactory)
    company = factory.SubFactory(CompanyFactory)
    status = MarketplaceOrder.Status.PENDING
    total_amount = Decimal("99.90")
    notes = factory.Faker("sentence")
    metadata = factory.LazyFunction(dict)
    ordered_at = factory.LazyFunction(timezone.now)


class MarketplaceOrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MarketplaceOrderItem

    order = factory.SubFactory(MarketplaceOrderFactory)
    product = factory.SubFactory(MarketplaceProductFactory)
    vendor = factory.SelfAttribute("product.vendor")
    quantity = 1
    unit_price = Decimal("99.90")
    status = MarketplaceOrderItem.Status.PERSONALIZATION_PENDING
    metadata = factory.LazyFunction(dict)


class MarketplaceCategoryFactory(factory.Factory):
    class Meta:
        model = dict

    id = factory.Sequence(lambda n: n + 1)
    name = factory.Sequence(lambda n: f"Category {n}")
    slug = factory.Sequence(lambda n: f"category-{n}")

