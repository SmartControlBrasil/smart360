from rest_framework import serializers

from ..models import (
    BillingAddon,
    BillingCustomer,
    BillingLedgerEntry,
    BillingPlan,
    CommissionStatement,
    Contract,
    CreditTransaction,
    CreditWallet,
    Invoice,
    InvoiceItem,
    PaymentRecord,
    Subscription,
    SubscriptionAddon,
)
from ..services.billing_service import (
    ContractService,
    CreditWalletService,
    InvoiceService,
    PaymentService,
    SubscriptionService,
)


class BillingCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingCustomer
        fields = (
            "id",
            "public_id",
            "user",
            "company",
            "external_reference",
            "customer_type",
            "billing_email",
            "document_number",
            "legal_name",
            "trade_name",
            "phone",
            "status",
            "notes",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class BillingPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingPlan
        fields = (
            "id",
            "public_id",
            "name",
            "slug",
            "description",
            "billing_interval",
            "price_amount",
            "price_monthly",
            "price_yearly",
            "currency",
            "trial_days",
            "user_limit",
            "asset_limit",
            "site_limit",
            "work_order_limit",
            "enabled_features",
            "status",
            "is_active",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class ContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = (
            "id",
            "public_id",
            "company",
            "billing_customer",
            "plan",
            "contract_code",
            "start_date",
            "renewal_date",
            "billing_periodicity",
            "contracted_amount",
            "status",
            "sales_owner",
            "notes",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "contract_code", "created_at", "updated_at")

    def create(self, validated_data):
        return ContractService.create_contract(**validated_data)


class BillingAddonSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingAddon
        fields = ("id", "public_id", "name", "slug", "description", "addon_type", "price_amount", "currency", "is_active", "metadata", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = (
            "id",
            "public_id",
            "billing_customer",
            "company",
            "contract",
            "plan",
            "status",
            "started_at",
            "current_period_start",
            "current_period_end",
            "next_billing_at",
            "amount",
            "billing_method",
            "cancelled_at",
            "trial_ends_at",
            "auto_renew",
            "notes",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "created_at", "updated_at")

    def create(self, validated_data):
        return SubscriptionService.create_subscription(**validated_data)


class SubscriptionAddonSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionAddon
        fields = ("id", "public_id", "subscription", "addon", "quantity", "status", "started_at", "ended_at", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = (
            "id",
            "public_id",
            "billing_customer",
            "company",
            "contract",
            "subscription",
            "invoice_number",
            "status",
            "subtotal_amount",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "currency",
            "issued_at",
            "due_at",
            "paid_at",
            "payment_method",
            "external_reference",
            "notes",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "invoice_number", "total_amount", "created_at", "updated_at")

    def create(self, validated_data):
        return InvoiceService.create_invoice(**validated_data)


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ("id", "public_id", "invoice", "item_type", "reference_type", "reference_id", "description", "quantity", "unit_amount", "total_amount", "metadata", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "total_amount", "created_at", "updated_at")

    def create(self, validated_data):
        return InvoiceService.add_item(**validated_data)


class PaymentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRecord
        fields = (
            "id",
            "public_id",
            "invoice",
            "provider",
            "provider_reference",
            "payment_method",
            "status",
            "amount",
            "currency",
            "paid_at",
            "metadata",
            "notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "created_at", "updated_at")

    def create(self, validated_data):
        return PaymentService.create_payment(**validated_data)


class CreditWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditWallet
        fields = ("id", "public_id", "billing_customer", "wallet_type", "balance", "currency", "is_active", "metadata", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class CreditTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditTransaction
        fields = ("id", "public_id", "wallet", "transaction_type", "amount", "balance_after", "reference_type", "reference_id", "description", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "balance_after", "created_at", "updated_at")

    def create(self, validated_data):
        return CreditWalletService.apply_transaction(**validated_data)


class BillingLedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingLedgerEntry
        fields = ("id", "public_id", "billing_customer", "entry_type", "amount", "currency", "reference_type", "reference_id", "description", "occurred_at", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class CommissionStatementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommissionStatement
        fields = ("id", "public_id", "billing_customer", "related_company", "statement_type", "gross_amount", "fee_amount", "net_amount", "currency", "status", "period_start", "period_end", "notes", "metadata", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "net_amount", "created_at", "updated_at")
