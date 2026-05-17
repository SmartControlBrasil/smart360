from django.test import TestCase

from apps.billing.models import BillingCustomer, BillingPlan, Contract, Subscription
from apps.billing.services.billing_service import BillingAccessService, ContractService, SubscriptionService
from tests.factories.core import CompanyFactory


class BillingAccessServiceTests(TestCase):
    def setUp(self):
        self.company = CompanyFactory(name="Panobianco", slug="panobianco")
        self.customer = BillingCustomer.objects.create(
            company=self.company,
            billing_email="financeiro@panobianco.local",
            customer_type=BillingCustomer.CustomerType.COMPANY,
            trade_name=self.company.name,
            legal_name=self.company.legal_name,
        )
        self.plan = BillingPlan.objects.create(
            name="Professional",
            slug="professional",
            billing_interval=BillingPlan.BillingInterval.MONTHLY,
            price_amount="799.00",
            price_monthly="799.00",
            price_yearly="7990.00",
            status=BillingPlan.Status.ACTIVE,
        )

    def test_contract_creation_keeps_company_binding(self):
        contract = ContractService.create_contract(
            company=self.company,
            billing_customer=self.customer,
            plan=self.plan,
            billing_periodicity=Contract.BillingPeriodicity.MONTHLY,
            contracted_amount="799.00",
            status=Contract.Status.ACTIVE,
        )

        self.assertEqual(contract.company, self.company)
        self.assertEqual(contract.plan, self.plan)

    def test_suspended_subscription_blocks_company_access(self):
        contract = ContractService.create_contract(
            company=self.company,
            billing_customer=self.customer,
            plan=self.plan,
            billing_periodicity=Contract.BillingPeriodicity.MONTHLY,
            contracted_amount="799.00",
            status=Contract.Status.ACTIVE,
        )
        SubscriptionService.create_subscription(
            billing_customer=self.customer,
            company=self.company,
            contract=contract,
            plan=self.plan,
            status=Subscription.Status.SUSPENDED,
            billing_method="manual",
            auto_renew=False,
        )

        context = BillingAccessService.get_company_billing_context(self.company)

        self.assertFalse(context["access_allowed"])
        self.assertEqual(context["access_status"], Subscription.Status.SUSPENDED)

    def test_past_due_subscription_keeps_access_with_warning(self):
        contract = ContractService.create_contract(
            company=self.company,
            billing_customer=self.customer,
            plan=self.plan,
            billing_periodicity=Contract.BillingPeriodicity.MONTHLY,
            contracted_amount="799.00",
            status=Contract.Status.ACTIVE,
        )
        SubscriptionService.create_subscription(
            billing_customer=self.customer,
            company=self.company,
            contract=contract,
            plan=self.plan,
            status=Subscription.Status.PAST_DUE,
            billing_method="pix",
            auto_renew=True,
        )

        context = BillingAccessService.get_company_billing_context(self.company)

        self.assertTrue(context["access_allowed"])
        self.assertEqual(context["access_status"], "overdue")
        self.assertIsNotNone(context["warning"])
