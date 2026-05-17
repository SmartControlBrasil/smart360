import django.db.models.deletion
import django.utils.timezone
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BillingAddon",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("description", models.TextField(blank=True)),
                (
                    "addon_type",
                    models.CharField(
                        choices=[
                            ("storage", "Storage"),
                            ("support", "Support"),
                            ("credit", "Credit"),
                            ("feature", "Feature"),
                            ("listing", "Listing"),
                            ("custom", "Custom"),
                        ],
                        default="custom",
                        max_length=20,
                    ),
                ),
                ("price_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("currency", models.CharField(default="BRL", max_length=8)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "billing_addons", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="BillingCustomer",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("external_reference", models.CharField(blank=True, max_length=120)),
                (
                    "customer_type",
                    models.CharField(
                        choices=[
                            ("individual", "Individual"),
                            ("company", "Company"),
                            ("marketplace_vendor", "Marketplace Vendor"),
                            ("internal", "Internal"),
                        ],
                        default="company",
                        max_length=30,
                    ),
                ),
                ("billing_email", models.EmailField(max_length=254)),
                ("document_number", models.CharField(blank=True, max_length=40)),
                ("legal_name", models.CharField(blank=True, max_length=180)),
                ("trade_name", models.CharField(blank=True, max_length=180)),
                ("phone", models.CharField(blank=True, max_length=30)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("inactive", "Inactive"),
                            ("delinquent", "Delinquent"),
                            ("suspended", "Suspended"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="billing_customers",
                        to="companies.company",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="billing_customers",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "billing_customers", "ordering": ["trade_name", "billing_email"]},
        ),
        migrations.CreateModel(
            name="BillingPlan",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("description", models.TextField(blank=True)),
                (
                    "billing_interval",
                    models.CharField(
                        choices=[("monthly", "Monthly"), ("yearly", "Yearly"), ("custom", "Custom")],
                        default="monthly",
                        max_length=20,
                    ),
                ),
                ("price_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("currency", models.CharField(default="BRL", max_length=8)),
                ("trial_days", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "billing_plans", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="BillingLedgerEntry",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "entry_type",
                    models.CharField(
                        choices=[
                            ("invoice_created", "Invoice Created"),
                            ("payment_received", "Payment Received"),
                            ("credit_added", "Credit Added"),
                            ("credit_spent", "Credit Spent"),
                            ("commission_reserved", "Commission Reserved"),
                            ("adjustment", "Adjustment"),
                        ],
                        default="adjustment",
                        max_length=30,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("currency", models.CharField(default="BRL", max_length=8)),
                ("reference_type", models.CharField(blank=True, max_length=80)),
                ("reference_id", models.CharField(blank=True, max_length=120)),
                ("description", models.CharField(max_length=255)),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "billing_customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ledger_entries",
                        to="billing.billingcustomer",
                    ),
                ),
            ],
            options={"db_table": "billing_ledger_entries", "ordering": ["-occurred_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="CommissionStatement",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "statement_type",
                    models.CharField(
                        choices=[
                            ("marketplace", "Marketplace"),
                            ("referral", "Referral"),
                            ("internal_production", "Internal Production"),
                            ("custom", "Custom"),
                        ],
                        default="custom",
                        max_length=30,
                    ),
                ),
                ("gross_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("fee_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("net_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("currency", models.CharField(default="BRL", max_length=8)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("calculated", "Calculated"),
                            ("approved", "Approved"),
                            ("paid", "Paid"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("period_start", models.DateField(blank=True, null=True)),
                ("period_end", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "billing_customer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="commission_statements",
                        to="billing.billingcustomer",
                    ),
                ),
                (
                    "related_company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="commission_statements",
                        to="companies.company",
                    ),
                ),
            ],
            options={"db_table": "billing_commission_statements", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="CreditWallet",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "wallet_type",
                    models.CharField(
                        choices=[
                            ("lead_credits", "Lead Credits"),
                            ("marketplace_credits", "Marketplace Credits"),
                            ("internal_credits", "Internal Credits"),
                            ("custom", "Custom"),
                        ],
                        default="custom",
                        max_length=30,
                    ),
                ),
                ("balance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("currency", models.CharField(default="BRL", max_length=8)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "billing_customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wallets",
                        to="billing.billingcustomer",
                    ),
                ),
            ],
            options={"db_table": "billing_credit_wallets", "ordering": ["billing_customer", "wallet_type"]},
        ),
        migrations.CreateModel(
            name="Subscription",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("trialing", "Trialing"),
                            ("active", "Active"),
                            ("past_due", "Past Due"),
                            ("cancelled", "Cancelled"),
                            ("expired", "Expired"),
                            ("suspended", "Suspended"),
                        ],
                        default="trialing",
                        max_length=20,
                    ),
                ),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("current_period_start", models.DateTimeField(default=django.utils.timezone.now)),
                ("current_period_end", models.DateTimeField()),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("trial_ends_at", models.DateTimeField(blank=True, null=True)),
                ("auto_renew", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "billing_customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="subscriptions",
                        to="billing.billingcustomer",
                    ),
                ),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subscriptions",
                        to="billing.billingplan",
                    ),
                ),
            ],
            options={"db_table": "billing_subscriptions", "ordering": ["-started_at"]},
        ),
        migrations.CreateModel(
            name="Invoice",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("invoice_number", models.CharField(blank=True, max_length=40, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("open", "Open"),
                            ("paid", "Paid"),
                            ("overdue", "Overdue"),
                            ("void", "Void"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("subtotal_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("discount_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("tax_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("total_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("currency", models.CharField(default="BRL", max_length=8)),
                ("issued_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("due_at", models.DateTimeField(blank=True, null=True)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "billing_customer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="invoices",
                        to="billing.billingcustomer",
                    ),
                ),
                (
                    "subscription",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="invoices",
                        to="billing.subscription",
                    ),
                ),
            ],
            options={"db_table": "billing_invoices", "ordering": ["-issued_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="CreditTransaction",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "transaction_type",
                    models.CharField(
                        choices=[
                            ("credit_added", "Credit Added"),
                            ("credit_spent", "Credit Spent"),
                            ("credit_expired", "Credit Expired"),
                            ("adjustment", "Adjustment"),
                        ],
                        default="credit_added",
                        max_length=20,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("balance_after", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=14)),
                ("reference_type", models.CharField(blank=True, max_length=80)),
                ("reference_id", models.CharField(blank=True, max_length=120)),
                ("description", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "wallet",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transactions",
                        to="billing.creditwallet",
                    ),
                ),
            ],
            options={"db_table": "billing_credit_transactions", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="InvoiceItem",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "item_type",
                    models.CharField(
                        choices=[
                            ("plan", "Plan"),
                            ("addon", "Addon"),
                            ("one_time", "One Time"),
                            ("credit", "Credit"),
                            ("adjustment", "Adjustment"),
                            ("commission", "Commission"),
                        ],
                        default="one_time",
                        max_length=20,
                    ),
                ),
                ("reference_type", models.CharField(blank=True, max_length=80)),
                ("reference_id", models.CharField(blank=True, max_length=120)),
                ("description", models.CharField(max_length=255)),
                ("quantity", models.DecimalField(decimal_places=2, default=Decimal("1.00"), max_digits=12)),
                ("unit_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("total_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "invoice",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="billing.invoice",
                    ),
                ),
            ],
            options={"db_table": "billing_invoice_items", "ordering": ["invoice__issued_at", "id"]},
        ),
        migrations.CreateModel(
            name="PaymentRecord",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("provider", models.CharField(max_length=80)),
                ("provider_reference", models.CharField(blank=True, max_length=120)),
                (
                    "payment_method",
                    models.CharField(
                        choices=[
                            ("pix", "Pix"),
                            ("credit_card", "Credit Card"),
                            ("bank_slip", "Bank Slip"),
                            ("transfer", "Transfer"),
                            ("internal", "Internal"),
                        ],
                        default="pix",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("authorized", "Authorized"),
                            ("paid", "Paid"),
                            ("failed", "Failed"),
                            ("refunded", "Refunded"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("currency", models.CharField(default="BRL", max_length=8)),
                ("paid_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "invoice",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="payments",
                        to="billing.invoice",
                    ),
                ),
            ],
            options={"db_table": "billing_payment_records", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SubscriptionAddon",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("quantity", models.PositiveIntegerField(default=1)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("paused", "Paused"),
                            ("cancelled", "Cancelled"),
                            ("expired", "Expired"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "addon",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subscription_links",
                        to="billing.billingaddon",
                    ),
                ),
                (
                    "subscription",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="addons",
                        to="billing.subscription",
                    ),
                ),
            ],
            options={"db_table": "billing_subscription_addons", "ordering": ["-started_at"]},
        ),
        migrations.AddConstraint(
            model_name="creditwallet",
            constraint=models.UniqueConstraint(fields=("billing_customer", "wallet_type"), name="uniq_customer_wallet_type"),
        ),
        migrations.AddConstraint(
            model_name="subscriptionaddon",
            constraint=models.UniqueConstraint(fields=("subscription", "addon"), name="uniq_subscription_addon_link"),
        ),
    ]
