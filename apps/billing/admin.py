from django.contrib import admin

from .models import (
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


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ("public_id", "created_at", "updated_at")


class SubscriptionAddonInline(admin.TabularInline):
    model = SubscriptionAddon
    extra = 0
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(BillingCustomer)
class BillingCustomerAdmin(admin.ModelAdmin):
    list_display = ("trade_name", "billing_email", "customer_type", "status", "created_at")
    list_filter = ("customer_type", "status")
    search_fields = ("trade_name", "legal_name", "billing_email", "document_number", "external_reference")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("user", "company")


@admin.register(BillingPlan)
class BillingPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "price_monthly", "price_yearly", "currency", "user_limit", "asset_limit")
    list_filter = ("billing_interval", "currency", "status", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("contract_code", "company", "plan", "billing_periodicity", "contracted_amount", "status", "renewal_date")
    list_filter = ("billing_periodicity", "status", "plan")
    search_fields = ("contract_code", "company__name", "plan__name", "notes")
    readonly_fields = ("public_id", "contract_code", "created_at", "updated_at")
    autocomplete_fields = ("company", "billing_customer", "plan", "sales_owner")


@admin.register(BillingAddon)
class BillingAddonAdmin(admin.ModelAdmin):
    list_display = ("name", "addon_type", "price_amount", "currency", "is_active")
    list_filter = ("addon_type", "currency", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("billing_customer", "company", "plan", "status", "amount", "next_billing_at", "auto_renew")
    list_filter = ("status", "auto_renew", "plan", "billing_method")
    search_fields = ("billing_customer__billing_email", "company__name", "plan__name", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("billing_customer", "company", "contract", "plan")
    inlines = (SubscriptionAddonInline,)


@admin.register(SubscriptionAddon)
class SubscriptionAddonAdmin(admin.ModelAdmin):
    list_display = ("subscription", "addon", "quantity", "status", "started_at")
    list_filter = ("status", "addon")
    search_fields = ("subscription__billing_customer__billing_email", "addon__name")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("subscription", "addon")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "company", "billing_customer", "status", "total_amount", "currency", "issued_at", "due_at")
    list_filter = ("status", "currency", "issued_at")
    search_fields = ("invoice_number", "billing_customer__billing_email", "company__name", "external_reference", "notes")
    readonly_fields = ("public_id", "invoice_number", "total_amount", "created_at", "updated_at")
    autocomplete_fields = ("billing_customer", "company", "contract", "subscription")
    inlines = (InvoiceItemInline,)


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ("invoice", "item_type", "description", "quantity", "total_amount")
    list_filter = ("item_type",)
    search_fields = ("invoice__invoice_number", "description", "reference_type", "reference_id")
    readonly_fields = ("public_id", "total_amount", "created_at", "updated_at")
    autocomplete_fields = ("invoice",)


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ("invoice", "provider", "payment_method", "status", "amount", "paid_at")
    list_filter = ("provider", "payment_method", "status")
    search_fields = ("invoice__invoice_number", "provider_reference", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("invoice",)


@admin.register(CreditWallet)
class CreditWalletAdmin(admin.ModelAdmin):
    list_display = ("billing_customer", "wallet_type", "balance", "currency", "is_active")
    list_filter = ("wallet_type", "currency", "is_active")
    search_fields = ("billing_customer__billing_email",)
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("billing_customer",)


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ("wallet", "transaction_type", "amount", "balance_after", "created_at")
    list_filter = ("transaction_type", "wallet__wallet_type")
    search_fields = ("wallet__billing_customer__billing_email", "reference_type", "reference_id", "description")
    readonly_fields = ("public_id", "balance_after", "created_at", "updated_at")
    autocomplete_fields = ("wallet",)


@admin.register(BillingLedgerEntry)
class BillingLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("billing_customer", "entry_type", "amount", "currency", "occurred_at")
    list_filter = ("entry_type", "currency")
    search_fields = ("billing_customer__billing_email", "reference_type", "reference_id", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("billing_customer",)


@admin.register(CommissionStatement)
class CommissionStatementAdmin(admin.ModelAdmin):
    list_display = ("statement_type", "billing_customer", "related_company", "net_amount", "currency", "status")
    list_filter = ("statement_type", "status", "currency")
    search_fields = ("billing_customer__billing_email", "related_company__name", "notes")
    readonly_fields = ("public_id", "net_amount", "created_at", "updated_at")
    autocomplete_fields = ("billing_customer", "related_company")
