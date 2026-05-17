from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone

from apps.billing.models import BillingCustomer, BillingPlan, Contract, Invoice, PaymentRecord, Subscription
from tests.factories.core import CompanyFactory, UserFactory


class BillingCustomerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BillingCustomer

    user = factory.SubFactory(UserFactory)
    company = factory.SubFactory(CompanyFactory)
    customer_type = BillingCustomer.CustomerType.COMPANY
    billing_email = factory.Sequence(lambda n: f"billing{n}@smart360.local")
    legal_name = factory.Sequence(lambda n: f"Billing Customer {n} LTDA")
    trade_name = factory.Sequence(lambda n: f"Billing Customer {n}")
    status = BillingCustomer.Status.ACTIVE
    metadata = factory.LazyFunction(dict)


class BillingPlanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BillingPlan

    name = factory.Sequence(lambda n: f"Billing Plan {n}")
    description = factory.Faker("sentence")
    billing_interval = BillingPlan.BillingInterval.MONTHLY
    price_amount = Decimal("199.00")
    price_monthly = Decimal("199.00")
    price_yearly = Decimal("1990.00")
    currency = "BRL"
    trial_days = 7
    user_limit = 10
    asset_limit = 100
    site_limit = 3
    work_order_limit = 250
    enabled_features = factory.LazyFunction(lambda: ["smart_system", "reports"])
    status = BillingPlan.Status.ACTIVE
    is_active = True
    metadata = factory.LazyFunction(dict)


class ContractFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Contract

    company = factory.SubFactory(CompanyFactory)
    billing_customer = factory.SubFactory(BillingCustomerFactory, company=factory.SelfAttribute("..company"))
    plan = factory.SubFactory(BillingPlanFactory)
    start_date = factory.LazyFunction(timezone.localdate)
    renewal_date = factory.LazyFunction(lambda: timezone.localdate() + timedelta(days=30))
    billing_periodicity = Contract.BillingPeriodicity.MONTHLY
    contracted_amount = Decimal("199.00")
    status = Contract.Status.ACTIVE
    metadata = factory.LazyFunction(dict)


class SubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subscription

    billing_customer = factory.SubFactory(BillingCustomerFactory)
    company = factory.SelfAttribute("billing_customer.company")
    contract = factory.SubFactory(ContractFactory, company=factory.SelfAttribute("..company"), billing_customer=factory.SelfAttribute("..billing_customer"))
    plan = factory.SubFactory(BillingPlanFactory)
    status = Subscription.Status.ACTIVE
    started_at = factory.LazyFunction(timezone.now)
    current_period_start = factory.LazyFunction(timezone.now)
    current_period_end = factory.LazyFunction(lambda: timezone.now() + timedelta(days=30))
    next_billing_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=30))
    amount = Decimal("199.00")
    billing_method = "manual"
    auto_renew = True
    metadata = factory.LazyFunction(dict)


class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invoice

    billing_customer = factory.SubFactory(BillingCustomerFactory)
    subscription = factory.SubFactory(SubscriptionFactory)
    company = factory.SelfAttribute("subscription.company")
    contract = factory.SelfAttribute("subscription.contract")
    status = Invoice.Status.OPEN
    subtotal_amount = Decimal("199.00")
    discount_amount = Decimal("0.00")
    tax_amount = Decimal("0.00")
    currency = "BRL"
    issued_at = factory.LazyFunction(timezone.now)
    due_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))
    payment_method = "pix"
    metadata = factory.LazyFunction(dict)


class PaymentRecordFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PaymentRecord

    invoice = factory.SubFactory(InvoiceFactory)
    provider = "internal-demo"
    payment_method = PaymentRecord.PaymentMethod.PIX
    status = PaymentRecord.Status.PENDING
    amount = Decimal("199.00")
    currency = "BRL"
    metadata = factory.LazyFunction(dict)
