import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class BillingCustomer(models.Model):
    class CustomerType(models.TextChoices):
        INDIVIDUAL = "individual", "Individual"
        COMPANY = "company", "Company"
        MARKETPLACE_VENDOR = "marketplace_vendor", "Marketplace Vendor"
        INTERNAL = "internal", "Internal"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        DELINQUENT = "delinquent", "Delinquent"
        SUSPENDED = "suspended", "Suspended"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="billing_customers",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="billing_customers",
        null=True,
        blank=True,
    )
    external_reference = models.CharField(max_length=120, blank=True)
    customer_type = models.CharField(max_length=30, choices=CustomerType.choices, default=CustomerType.COMPANY)
    billing_email = models.EmailField()
    document_number = models.CharField(max_length=40, blank=True)
    legal_name = models.CharField(max_length=180, blank=True)
    trade_name = models.CharField(max_length=180, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_customers"
        ordering = ["trade_name", "billing_email"]

    def __str__(self) -> str:
        return self.trade_name or self.legal_name or self.billing_email


class BillingPlan(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        ARCHIVED = "archived", "Archived"

    class BillingInterval(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"
        CUSTOM = "custom", "Custom"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    description = models.TextField(blank=True)
    billing_interval = models.CharField(max_length=20, choices=BillingInterval.choices, default=BillingInterval.MONTHLY)
    price_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    price_monthly = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    price_yearly = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="BRL")
    trial_days = models.PositiveIntegerField(default=0)
    user_limit = models.PositiveIntegerField(default=0)
    asset_limit = models.PositiveIntegerField(default=0)
    site_limit = models.PositiveIntegerField(default=0)
    work_order_limit = models.PositiveIntegerField(default=0)
    enabled_features = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_plans"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if self.price_monthly == Decimal("0.00") and self.billing_interval == self.BillingInterval.MONTHLY:
            self.price_monthly = self.price_amount
        if self.price_yearly == Decimal("0.00") and self.billing_interval == self.BillingInterval.YEARLY:
            self.price_yearly = self.price_amount
        self.is_active = self.status == self.Status.ACTIVE
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class BillingAddon(models.Model):
    class AddonType(models.TextChoices):
        STORAGE = "storage", "Storage"
        SUPPORT = "support", "Support"
        CREDIT = "credit", "Credit"
        FEATURE = "feature", "Feature"
        LISTING = "listing", "Listing"
        CUSTOM = "custom", "Custom"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    description = models.TextField(blank=True)
    addon_type = models.CharField(max_length=20, choices=AddonType.choices, default=AddonType.CUSTOM)
    price_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="BRL")
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_addons"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Contract(models.Model):
    class BillingPeriodicity(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="billing_contracts")
    billing_customer = models.ForeignKey(
        "billing.BillingCustomer",
        on_delete=models.SET_NULL,
        related_name="contracts",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey("billing.BillingPlan", on_delete=models.PROTECT, related_name="contracts")
    contract_code = models.CharField(max_length=40, unique=True, blank=True)
    start_date = models.DateField(default=timezone.localdate)
    renewal_date = models.DateField(null=True, blank=True)
    billing_periodicity = models.CharField(
        max_length=20,
        choices=BillingPeriodicity.choices,
        default=BillingPeriodicity.MONTHLY,
    )
    contracted_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    sales_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="managed_contracts",
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_contracts"
        ordering = ["-start_date", "-created_at"]

    def save(self, *args, **kwargs):
        if not self.contract_code:
            prefix = timezone.now().strftime("CTR-%Y%m")
            latest = Contract.objects.filter(contract_code__startswith=prefix).order_by("-contract_code").first()
            sequence = int(latest.contract_code.split("-")[-1]) + 1 if latest and latest.contract_code else 1
            self.contract_code = f"{prefix}-{sequence:04d}"
        if self.contracted_amount == Decimal("0.00"):
            if self.billing_periodicity == self.BillingPeriodicity.YEARLY:
                self.contracted_amount = self.plan.price_yearly or self.plan.price_amount
            else:
                self.contracted_amount = self.plan.price_monthly or self.plan.price_amount
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.contract_code or f"Contract {self.company}"


class Subscription(models.Model):
    class Status(models.TextChoices):
        TRIALING = "trialing", "Trialing"
        ACTIVE = "active", "Active"
        PAST_DUE = "past_due", "Past Due"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        SUSPENDED = "suspended", "Suspended"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    billing_customer = models.ForeignKey("billing.BillingCustomer", on_delete=models.CASCADE, related_name="subscriptions")
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="billing_subscriptions",
        null=True,
        blank=True,
    )
    contract = models.ForeignKey(
        "billing.Contract",
        on_delete=models.SET_NULL,
        related_name="subscriptions",
        null=True,
        blank=True,
    )
    plan = models.ForeignKey("billing.BillingPlan", on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.TRIALING)
    started_at = models.DateTimeField(default=timezone.now)
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField()
    next_billing_at = models.DateTimeField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    billing_method = models.CharField(max_length=30, default="manual")
    cancelled_at = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_subscriptions"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.billing_customer} - {self.plan}"


class SubscriptionAddon(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    subscription = models.ForeignKey("billing.Subscription", on_delete=models.CASCADE, related_name="addons")
    addon = models.ForeignKey("billing.BillingAddon", on_delete=models.PROTECT, related_name="subscription_links")
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_subscription_addons"
        ordering = ["-started_at"]
        constraints = [
            models.UniqueConstraint(fields=["subscription", "addon"], name="uniq_subscription_addon_link"),
        ]

    def __str__(self) -> str:
        return f"{self.subscription} + {self.addon}"


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        VOID = "void", "Void"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    billing_customer = models.ForeignKey("billing.BillingCustomer", on_delete=models.CASCADE, related_name="invoices")
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="billing_invoices",
        null=True,
        blank=True,
    )
    contract = models.ForeignKey(
        "billing.Contract",
        on_delete=models.SET_NULL,
        related_name="invoices",
        null=True,
        blank=True,
    )
    subscription = models.ForeignKey(
        "billing.Subscription",
        on_delete=models.SET_NULL,
        related_name="invoices",
        null=True,
        blank=True,
    )
    invoice_number = models.CharField(max_length=40, unique=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="BRL")
    issued_at = models.DateTimeField(default=timezone.now)
    due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_method = models.CharField(max_length=30, blank=True)
    external_reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_invoices"
        ordering = ["-issued_at", "-created_at"]

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            prefix = timezone.now().strftime("INV-%Y%m%d")
            latest = Invoice.objects.filter(invoice_number__startswith=prefix).order_by("-invoice_number").first()
            sequence = int(latest.invoice_number.split("-")[-1]) + 1 if latest and latest.invoice_number else 1
            self.invoice_number = f"{prefix}-{sequence:04d}"
        self.total_amount = (self.subtotal_amount or Decimal("0.00")) - (self.discount_amount or Decimal("0.00")) + (
            self.tax_amount or Decimal("0.00")
        )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.invoice_number


class InvoiceItem(models.Model):
    class ItemType(models.TextChoices):
        PLAN = "plan", "Plan"
        ADDON = "addon", "Addon"
        ONE_TIME = "one_time", "One Time"
        CREDIT = "credit", "Credit"
        ADJUSTMENT = "adjustment", "Adjustment"
        COMMISSION = "commission", "Commission"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    invoice = models.ForeignKey("billing.Invoice", on_delete=models.CASCADE, related_name="items")
    item_type = models.CharField(max_length=20, choices=ItemType.choices, default=ItemType.ONE_TIME)
    reference_type = models.CharField(max_length=80, blank=True)
    reference_id = models.CharField(max_length=120, blank=True)
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("1.00"))
    unit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_invoice_items"
        ordering = ["invoice__issued_at", "id"]

    def save(self, *args, **kwargs):
        self.total_amount = (self.quantity or Decimal("0.00")) * (self.unit_amount or Decimal("0.00"))
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.description


class PaymentRecord(models.Model):
    class PaymentMethod(models.TextChoices):
        PIX = "pix", "Pix"
        CREDIT_CARD = "credit_card", "Credit Card"
        BANK_SLIP = "bank_slip", "Bank Slip"
        TRANSFER = "transfer", "Transfer"
        INTERNAL = "internal", "Internal"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        AUTHORIZED = "authorized", "Authorized"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    invoice = models.ForeignKey("billing.Invoice", on_delete=models.CASCADE, related_name="payments")
    provider = models.CharField(max_length=80)
    provider_reference = models.CharField(max_length=120, blank=True)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.PIX)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="BRL")
    paid_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_payment_records"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.invoice} - {self.amount}"


class CreditWallet(models.Model):
    class WalletType(models.TextChoices):
        LEAD_CREDITS = "lead_credits", "Lead Credits"
        MARKETPLACE_CREDITS = "marketplace_credits", "Marketplace Credits"
        INTERNAL_CREDITS = "internal_credits", "Internal Credits"
        CUSTOM = "custom", "Custom"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    billing_customer = models.ForeignKey("billing.BillingCustomer", on_delete=models.CASCADE, related_name="wallets")
    wallet_type = models.CharField(max_length=30, choices=WalletType.choices, default=WalletType.CUSTOM)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="BRL")
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_credit_wallets"
        ordering = ["billing_customer", "wallet_type"]
        constraints = [
            models.UniqueConstraint(fields=["billing_customer", "wallet_type"], name="uniq_customer_wallet_type"),
        ]

    def __str__(self) -> str:
        return f"{self.billing_customer} - {self.wallet_type}"


class CreditTransaction(models.Model):
    class TransactionType(models.TextChoices):
        CREDIT_ADDED = "credit_added", "Credit Added"
        CREDIT_SPENT = "credit_spent", "Credit Spent"
        CREDIT_EXPIRED = "credit_expired", "Credit Expired"
        ADJUSTMENT = "adjustment", "Adjustment"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    wallet = models.ForeignKey("billing.CreditWallet", on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices, default=TransactionType.CREDIT_ADDED)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    reference_type = models.CharField(max_length=80, blank=True)
    reference_id = models.CharField(max_length=120, blank=True)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_credit_transactions"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.transaction_type} {self.amount}"


class BillingLedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        INVOICE_CREATED = "invoice_created", "Invoice Created"
        PAYMENT_RECEIVED = "payment_received", "Payment Received"
        CREDIT_ADDED = "credit_added", "Credit Added"
        CREDIT_SPENT = "credit_spent", "Credit Spent"
        COMMISSION_RESERVED = "commission_reserved", "Commission Reserved"
        ADJUSTMENT = "adjustment", "Adjustment"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    billing_customer = models.ForeignKey("billing.BillingCustomer", on_delete=models.CASCADE, related_name="ledger_entries")
    entry_type = models.CharField(max_length=30, choices=EntryType.choices, default=EntryType.ADJUSTMENT)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default="BRL")
    reference_type = models.CharField(max_length=80, blank=True)
    reference_id = models.CharField(max_length=120, blank=True)
    description = models.CharField(max_length=255)
    occurred_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_ledger_entries"
        ordering = ["-occurred_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.billing_customer} - {self.entry_type}"


class CommissionStatement(models.Model):
    class StatementType(models.TextChoices):
        MARKETPLACE = "marketplace", "Marketplace"
        REFERRAL = "referral", "Referral"
        INTERNAL_PRODUCTION = "internal_production", "Internal Production"
        CUSTOM = "custom", "Custom"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CALCULATED = "calculated", "Calculated"
        APPROVED = "approved", "Approved"
        PAID = "paid", "Paid"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    billing_customer = models.ForeignKey(
        "billing.BillingCustomer",
        on_delete=models.SET_NULL,
        related_name="commission_statements",
        null=True,
        blank=True,
    )
    related_company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="commission_statements",
        null=True,
        blank=True,
    )
    statement_type = models.CharField(max_length=30, choices=StatementType.choices, default=StatementType.CUSTOM)
    gross_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    fee_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    net_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=8, default="BRL")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "billing_commission_statements"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.net_amount = (self.gross_amount or Decimal("0.00")) - (self.fee_amount or Decimal("0.00"))
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.statement_type} - {self.net_amount}"
