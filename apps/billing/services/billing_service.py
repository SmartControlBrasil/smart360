from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.observability_center.models import ErrorIncident, SystemEventLog
from apps.observability_center.services.observability_service import (
    ErrorIncidentService,
    MetricCounterService,
    SystemEventService,
)

from ..models import (
    BillingCustomer,
    BillingPlan,
    BillingLedgerEntry,
    Contract,
    CreditTransaction,
    Invoice,
    InvoiceItem,
    PaymentRecord,
    Subscription,
)


class LedgerService:
    @staticmethod
    def create_entry(*, billing_customer, entry_type, amount, currency, description, reference_type="", reference_id=""):
        return BillingLedgerEntry.objects.create(
            billing_customer=billing_customer,
            entry_type=entry_type,
            amount=amount,
            currency=currency,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
        )


class SubscriptionService:
    @staticmethod
    def _calculate_period_end(*, start_at, interval):
        if interval == "yearly":
            return start_at + timedelta(days=365)
        if interval == "custom":
            return start_at + timedelta(days=30)
        return start_at + timedelta(days=30)

    @staticmethod
    @transaction.atomic
    def create_subscription(**validated_data):
        start_at = validated_data.get("started_at") or timezone.now()
        plan = validated_data["plan"]
        company = validated_data.get("company") or getattr(validated_data.get("billing_customer"), "company", None)
        contract = validated_data.get("contract")
        trial_days = plan.trial_days or 0
        if not validated_data.get("trial_ends_at") and trial_days:
            validated_data["trial_ends_at"] = start_at + timedelta(days=trial_days)
        if not validated_data.get("current_period_start"):
            validated_data["current_period_start"] = start_at
        if not validated_data.get("current_period_end"):
            validated_data["current_period_end"] = SubscriptionService._calculate_period_end(
                start_at=validated_data["current_period_start"],
                interval=plan.billing_interval,
            )
        if not validated_data.get("next_billing_at"):
            validated_data["next_billing_at"] = validated_data["current_period_end"]
        if not validated_data.get("amount"):
            if plan.billing_interval == BillingPlan.BillingInterval.YEARLY:
                validated_data["amount"] = plan.price_yearly or plan.price_amount
            else:
                validated_data["amount"] = plan.price_monthly or plan.price_amount
        if company is not None:
            validated_data["company"] = company
        if contract is not None:
            validated_data["contract"] = contract
        subscription = Subscription.objects.create(**validated_data)
        return subscription

    @staticmethod
    def cancel_subscription(*, subscription):
        subscription.status = Subscription.Status.CANCELLED
        subscription.cancelled_at = timezone.now()
        subscription.auto_renew = False
        subscription.save(update_fields=["status", "cancelled_at", "auto_renew", "updated_at"])
        return subscription


class InvoiceService:
    @staticmethod
    @transaction.atomic
    def create_invoice(**validated_data):
        billing_customer = validated_data["billing_customer"]
        if not validated_data.get("company") and billing_customer.company_id:
            validated_data["company"] = billing_customer.company
        if not validated_data.get("contract") and validated_data.get("subscription") and validated_data["subscription"].contract_id:
            validated_data["contract"] = validated_data["subscription"].contract
        invoice = Invoice.objects.create(**validated_data)
        LedgerService.create_entry(
            billing_customer=invoice.billing_customer,
            entry_type=BillingLedgerEntry.EntryType.INVOICE_CREATED,
            amount=invoice.total_amount,
            currency=invoice.currency,
            description=f"Invoice {invoice.invoice_number} created",
            reference_type="invoice",
            reference_id=invoice.invoice_number,
        )
        return invoice

    @staticmethod
    @transaction.atomic
    def add_item(**validated_data):
        invoice = validated_data["invoice"]
        item = InvoiceItem.objects.create(**validated_data)
        subtotal = sum((invoice_item.total_amount for invoice_item in invoice.items.all()), Decimal("0.00"))
        invoice.subtotal_amount = subtotal
        invoice.save(update_fields=["subtotal_amount", "total_amount", "updated_at"])
        return item


class PaymentService:
    @staticmethod
    @transaction.atomic
    def create_payment(**validated_data):
        payment = PaymentRecord.objects.create(**validated_data)
        if payment.status == PaymentRecord.Status.PAID:
            PaymentService.mark_paid(payment=payment)
        return payment

    @staticmethod
    @transaction.atomic
    def mark_paid(*, payment):
        try:
            payment.status = PaymentRecord.Status.PAID
            payment.paid_at = payment.paid_at or timezone.now()
            payment.save(update_fields=["status", "paid_at", "updated_at"])

            invoice = payment.invoice
            invoice.status = Invoice.Status.PAID
            invoice.paid_at = payment.paid_at
            invoice.save(update_fields=["status", "paid_at", "updated_at"])

            LedgerService.create_entry(
                billing_customer=invoice.billing_customer,
                entry_type=BillingLedgerEntry.EntryType.PAYMENT_RECEIVED,
                amount=payment.amount,
                currency=payment.currency,
                description=f"Payment received for invoice {invoice.invoice_number}",
                reference_type="payment",
                reference_id=str(payment.public_id),
            )
            MetricCounterService.increment_metric(
                metric_key="billing.payment_received_count",
                source_module="billing",
            )
            SystemEventService.log_system_event(
                event_type="billing.payment_record_paid",
                source_module="billing",
                severity=SystemEventLog.Severity.INFO,
                entity_type="invoice",
                entity_id=invoice.invoice_number,
                message=f"Payment registered for invoice {invoice.invoice_number}.",
                payload={"payment_id": str(payment.public_id), "amount": str(payment.amount)},
            )
            return payment
        except Exception as exc:  # pragma: no cover - defensive path
            ErrorIncidentService.register_error_incident(
                incident_key=f"billing:payment:{payment.public_id}",
                source_module="billing",
                error_type=exc.__class__.__name__,
                message="Failed to mark payment as paid.",
                severity=ErrorIncident.Severity.HIGH,
                payload={"payment_id": str(payment.public_id)},
            )
            raise


class CreditWalletService:
    @staticmethod
    @transaction.atomic
    def apply_transaction(**validated_data):
        wallet = validated_data["wallet"]
        amount = validated_data["amount"]
        if validated_data["transaction_type"] in {
            CreditTransaction.TransactionType.CREDIT_SPENT,
            CreditTransaction.TransactionType.CREDIT_EXPIRED,
        }:
            balance_after = wallet.balance - amount
        else:
            balance_after = wallet.balance + amount
        wallet.balance = balance_after
        wallet.save(update_fields=["balance", "updated_at"])

        transaction = CreditTransaction.objects.create(balance_after=balance_after, **validated_data)
        LedgerService.create_entry(
            billing_customer=wallet.billing_customer,
            entry_type=(
                BillingLedgerEntry.EntryType.CREDIT_SPENT
                if validated_data["transaction_type"] == CreditTransaction.TransactionType.CREDIT_SPENT
                else BillingLedgerEntry.EntryType.CREDIT_ADDED
            ),
            amount=amount,
            currency=wallet.currency,
            description=validated_data["description"],
            reference_type=validated_data.get("reference_type", "wallet"),
            reference_id=validated_data.get("reference_id", str(transaction.public_id)),
        )
        return transaction


class ContractService:
    @staticmethod
    @transaction.atomic
    def create_contract(**validated_data):
        company = validated_data["company"]
        billing_customer = validated_data.get("billing_customer")
        if billing_customer is None:
            billing_customer, _ = BillingCustomer.objects.get_or_create(
                company=company,
                defaults={
                    "billing_email": company.email or f"financeiro@{company.slug}.local",
                    "customer_type": BillingCustomer.CustomerType.COMPANY,
                    "trade_name": company.name,
                    "legal_name": company.legal_name,
                    "document_number": company.tax_id,
                    "status": BillingCustomer.Status.ACTIVE,
                },
            )
            validated_data["billing_customer"] = billing_customer
        contract = Contract.objects.create(**validated_data)
        return contract

    @staticmethod
    @transaction.atomic
    def suspend_contract(*, contract, reason=""):
        contract.status = Contract.Status.SUSPENDED
        contract.notes = f"{contract.notes}\n{reason}".strip()
        contract.save(update_fields=["status", "notes", "updated_at"])
        if contract.company_id:
            Subscription.objects.filter(company_id=contract.company_id).exclude(
                status=Subscription.Status.CANCELLED
            ).update(status=Subscription.Status.SUSPENDED, updated_at=timezone.now())
        return contract

    @staticmethod
    @transaction.atomic
    def cancel_contract(*, contract, reason=""):
        contract.status = Contract.Status.CANCELLED
        contract.notes = f"{contract.notes}\n{reason}".strip()
        contract.save(update_fields=["status", "notes", "updated_at"])
        if contract.company_id:
            Subscription.objects.filter(company_id=contract.company_id).exclude(
                status=Subscription.Status.CANCELLED
            ).update(
                status=Subscription.Status.CANCELLED,
                cancelled_at=timezone.now(),
                updated_at=timezone.now(),
            )
        return contract


class BillingAccessService:
    BLOCKED_SUBSCRIPTION_STATUSES = {
        Subscription.Status.SUSPENDED,
        Subscription.Status.CANCELLED,
        Subscription.Status.EXPIRED,
    }
    WARNING_SUBSCRIPTION_STATUSES = {Subscription.Status.PAST_DUE}

    @classmethod
    def get_company_billing_context(cls, company):
        if company is None:
            return {
                "company": None,
                "customer": None,
                "contract": None,
                "subscription": None,
                "plan": None,
                "access_status": "unscoped",
                "access_allowed": True,
                "warning": None,
            }

        customer = BillingCustomer.objects.filter(company=company).order_by("-created_at").first()
        contract = Contract.objects.filter(company=company).order_by("-created_at").first()
        subscription = Subscription.objects.filter(company=company).order_by("-created_at").first()
        plan = subscription.plan if subscription else contract.plan if contract else None

        access_status = "active"
        access_allowed = True
        warning = None

        if subscription is None and contract and contract.status == Contract.Status.SUSPENDED:
            access_status = "suspended"
            access_allowed = False
        elif subscription is None and contract and contract.status == Contract.Status.CANCELLED:
            access_status = "cancelled"
            access_allowed = False
        elif subscription is not None:
            if subscription.status in cls.BLOCKED_SUBSCRIPTION_STATUSES:
                access_status = subscription.status
                access_allowed = False
            elif subscription.status in cls.WARNING_SUBSCRIPTION_STATUSES:
                access_status = "overdue"
                warning = "Empresa com assinatura em atraso. O acesso segue liberado com aviso."
            elif subscription.status == Subscription.Status.TRIALING:
                access_status = "trial"

        return {
            "company": company,
            "customer": customer,
            "contract": contract,
            "subscription": subscription,
            "plan": plan,
            "access_status": access_status,
            "access_allowed": access_allowed,
            "warning": warning,
        }


class BillingDashboardService:
    @staticmethod
    def get_summary():
        subscriptions = Subscription.objects.select_related("company", "plan").all()
        invoices = Invoice.objects.select_related("company").all()
        contracts = Contract.objects.select_related("company", "plan").all()

        active_subscriptions = subscriptions.filter(status=Subscription.Status.ACTIVE)
        mrr = sum((subscription.amount for subscription in active_subscriptions), Decimal("0.00"))
        return {
            "mrr": mrr,
            "active_companies": active_subscriptions.values("company_id").distinct().count(),
            "trial_companies": subscriptions.filter(status=Subscription.Status.TRIALING).values("company_id").distinct().count(),
            "overdue_companies": subscriptions.filter(status=Subscription.Status.PAST_DUE).values("company_id").distinct().count(),
            "active_contracts": contracts.filter(status=Contract.Status.ACTIVE).count(),
            "pending_invoices": invoices.filter(status__in=[Invoice.Status.DRAFT, Invoice.Status.OPEN]).count(),
            "paid_invoices": invoices.filter(status=Invoice.Status.PAID).count(),
        }
