from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.companies.models import Company
from apps.users.models import User

from ..models import BillingCustomer, BillingLedgerEntry, Contract, CreditTransaction, Invoice, PaymentRecord, Subscription


class BillingApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="billing@smart360.local",
            password="StrongPass123",
            first_name="Billing",
        )
        self.company = Company.objects.create(
            name="Billing Co",
            slug="billing-co",
            status=Company.Status.ACTIVE,
        )
        self.client.force_authenticate(self.user)
        self.customer = BillingCustomer.objects.create(
            user=self.user,
            company=self.company,
            billing_email="finance@billing.co",
            customer_type=BillingCustomer.CustomerType.COMPANY,
            trade_name="Billing Co",
        )

    def test_create_subscription(self):
        plan_response = self.client.post(
            reverse("billing-plans-list"),
            {
                "name": "Smart System Pro",
                "description": "Recurring maintenance management plan",
                "billing_interval": "monthly",
                "price_amount": "299.90",
                "price_monthly": "299.90",
                "price_yearly": "2999.00",
                "currency": "BRL",
                "trial_days": 7,
                "user_limit": 20,
                "asset_limit": 500,
                "site_limit": 10,
                "work_order_limit": 5000,
                "enabled_features": ["smart_system", "reports", "preventive_plans"],
                "status": "active",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(plan_response.status_code, status.HTTP_201_CREATED)

        contract_response = self.client.post(
            reverse("billing-contracts-list"),
            {
                "company": self.company.id,
                "billing_customer": self.customer.id,
                "plan": plan_response.data["id"],
                "billing_periodicity": "monthly",
                "contracted_amount": "299.90",
                "status": "active",
            },
            format="json",
        )
        self.assertEqual(contract_response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(
            reverse("billing-subscriptions-list"),
            {
                "billing_customer": self.customer.id,
                "company": self.company.id,
                "contract": contract_response.data["id"],
                "plan": plan_response.data["id"],
                "status": "trialing",
                "billing_method": "manual",
                "auto_renew": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Subscription.objects.filter(billing_customer=self.customer).exists())
        subscription = Subscription.objects.get(billing_customer=self.customer)
        self.assertEqual(subscription.company, self.company)
        self.assertEqual(subscription.contract_id, contract_response.data["id"])

    def test_create_plan_with_commercial_limits(self):
        response = self.client.post(
            reverse("billing-plans-list"),
            {
                "name": "Enterprise",
                "description": "Plano anual enterprise",
                "billing_interval": "yearly",
                "price_amount": "14900.00",
                "price_monthly": "1490.00",
                "price_yearly": "14900.00",
                "currency": "BRL",
                "trial_days": 14,
                "user_limit": 0,
                "asset_limit": 0,
                "site_limit": 0,
                "work_order_limit": 0,
                "enabled_features": ["smart_system", "reports", "inventory"],
                "status": "active",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["price_yearly"], "14900.00")
        self.assertEqual(response.data["status"], "active")
        self.assertEqual(response.data["enabled_features"], ["smart_system", "reports", "inventory"])

    def test_create_invoice_and_payment(self):
        plan = self.client.post(
            reverse("billing-plans-list"),
            {
                "name": "Starter",
                "billing_interval": "monthly",
                "price_amount": "120.00",
                "price_monthly": "120.00",
                "price_yearly": "1200.00",
                "status": "active",
            },
            format="json",
        ).data
        contract = self.client.post(
            reverse("billing-contracts-list"),
            {
                "company": self.company.id,
                "billing_customer": self.customer.id,
                "plan": plan["id"],
                "billing_periodicity": "monthly",
                "contracted_amount": "120.00",
                "status": "active",
            },
            format="json",
        ).data
        subscription = self.client.post(
            reverse("billing-subscriptions-list"),
            {
                "billing_customer": self.customer.id,
                "company": self.company.id,
                "contract": contract["id"],
                "plan": plan["id"],
                "status": "active",
                "billing_method": "pix",
                "amount": "120.00",
                "auto_renew": True,
            },
            format="json",
        ).data
        invoice_response = self.client.post(
            reverse("billing-invoices-list"),
            {
                "billing_customer": self.customer.id,
                "company": self.company.id,
                "contract": contract["id"],
                "subscription": subscription["id"],
                "status": "open",
                "subtotal_amount": "120.00",
                "discount_amount": "10.00",
                "tax_amount": "5.00",
                "currency": "BRL",
                "payment_method": "pix",
            },
            format="json",
        )
        self.assertEqual(invoice_response.status_code, status.HTTP_201_CREATED)
        invoice = Invoice.objects.get(id=invoice_response.data["id"])
        self.assertEqual(invoice.company, self.company)
        self.assertEqual(invoice.contract_id, contract["id"])

        payment_response = self.client.post(
            reverse("billing-payment-records-list"),
            {
                "invoice": invoice.id,
                "provider": "manual",
                "payment_method": "pix",
                "status": "paid",
                "amount": "115.00",
                "currency": "BRL",
            },
            format="json",
        )
        self.assertEqual(payment_response.status_code, status.HTTP_201_CREATED)
        payment = PaymentRecord.objects.get(id=payment_response.data["id"])
        self.assertEqual(payment.status, PaymentRecord.Status.PAID)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertTrue(BillingLedgerEntry.objects.filter(billing_customer=self.customer).exists())

    def test_credit_transaction_updates_wallet(self):
        wallet_response = self.client.post(
            reverse("billing-wallets-list"),
            {
                "billing_customer": self.customer.id,
                "wallet_type": "lead_credits",
                "balance": "0.00",
                "currency": "BRL",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(wallet_response.status_code, status.HTTP_201_CREATED)

        transaction_response = self.client.post(
            reverse("billing-credit-transactions-list"),
            {
                "wallet": wallet_response.data["id"],
                "transaction_type": "credit_added",
                "amount": "50.00",
                "description": "Initial lead credits",
            },
            format="json",
        )
        self.assertEqual(transaction_response.status_code, status.HTTP_201_CREATED)
        transaction = CreditTransaction.objects.get(id=transaction_response.data["id"])
        self.assertEqual(transaction.balance_after, transaction.amount)

    def test_contract_dashboard_summary_returns_payload(self):
        response = self.client.get(reverse("billing-contracts-dashboard-summary"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("mrr", response.data)
        self.assertIn("active_contracts", response.data)
