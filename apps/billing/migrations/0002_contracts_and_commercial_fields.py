import django.db.models.deletion
import django.utils.timezone
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import migrations, models


def backfill_billing_plan_fields(apps, schema_editor):
    BillingPlan = apps.get_model("billing", "BillingPlan")
    for plan in BillingPlan.objects.all():
        updated_fields = []
        if plan.price_monthly == Decimal("0.00") and plan.billing_interval == "monthly":
            plan.price_monthly = plan.price_amount
            updated_fields.append("price_monthly")
        if plan.price_yearly == Decimal("0.00") and plan.billing_interval == "yearly":
            plan.price_yearly = plan.price_amount
            updated_fields.append("price_yearly")
        if plan.status == "":
            plan.status = "active"
            updated_fields.append("status")
        if updated_fields:
            plan.save(update_fields=updated_fields)


def backfill_subscription_and_invoice_scope(apps, schema_editor):
    Contract = apps.get_model("billing", "Contract")
    Subscription = apps.get_model("billing", "Subscription")
    Invoice = apps.get_model("billing", "Invoice")

    for subscription in Subscription.objects.select_related("billing_customer", "plan").all():
        updated_fields = []
        company = getattr(subscription.billing_customer, "company", None)
        if company and subscription.company_id is None:
            subscription.company_id = company.id
            updated_fields.append("company")
        if subscription.amount == Decimal("0.00"):
            subscription.amount = subscription.plan.price_monthly or subscription.plan.price_amount
            updated_fields.append("amount")
        if subscription.next_billing_at is None:
            subscription.next_billing_at = subscription.current_period_end
            updated_fields.append("next_billing_at")
        if updated_fields:
            subscription.save(update_fields=updated_fields)

        if subscription.contract_id is None and company:
            contract = Contract.objects.filter(company_id=company.id, status="active").order_by("-created_at").first()
            if contract:
                subscription.contract_id = contract.id
                subscription.save(update_fields=["contract"])

    for invoice in Invoice.objects.select_related("billing_customer", "subscription").all():
        updated_fields = []
        company = getattr(invoice.billing_customer, "company", None)
        if company and invoice.company_id is None:
            invoice.company_id = company.id
            updated_fields.append("company")
        if invoice.subscription_id and invoice.contract_id is None and getattr(invoice.subscription, "contract_id", None):
            invoice.contract_id = invoice.subscription.contract_id
            updated_fields.append("contract")
        if updated_fields:
            invoice.save(update_fields=updated_fields)


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="billingplan",
            name="asset_limit",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="billingplan",
            name="enabled_features",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="billingplan",
            name="price_monthly",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
        migrations.AddField(
            model_name="billingplan",
            name="price_yearly",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
        migrations.AddField(
            model_name="billingplan",
            name="site_limit",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="billingplan",
            name="status",
            field=models.CharField(
                choices=[("active", "Active"), ("inactive", "Inactive"), ("archived", "Archived")],
                default="active",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="billingplan",
            name="user_limit",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="billingplan",
            name="work_order_limit",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name="Contract",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("contract_code", models.CharField(blank=True, max_length=40, unique=True)),
                ("start_date", models.DateField(default=django.utils.timezone.localdate)),
                ("renewal_date", models.DateField(blank=True, null=True)),
                (
                    "billing_periodicity",
                    models.CharField(
                        choices=[("monthly", "Monthly"), ("yearly", "Yearly")],
                        default="monthly",
                        max_length=20,
                    ),
                ),
                ("contracted_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("suspended", "Suspended"),
                            ("cancelled", "Cancelled"),
                            ("expired", "Expired"),
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
                    "billing_customer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="contracts",
                        to="billing.billingcustomer",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="billing_contracts",
                        to="companies.company",
                    ),
                ),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="contracts",
                        to="billing.billingplan",
                    ),
                ),
                (
                    "sales_owner",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="managed_contracts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "billing_contracts", "ordering": ["-start_date", "-created_at"]},
        ),
        migrations.AddField(
            model_name="subscription",
            name="amount",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
        migrations.AddField(
            model_name="subscription",
            name="billing_method",
            field=models.CharField(default="manual", max_length=30),
        ),
        migrations.AddField(
            model_name="subscription",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="billing_subscriptions",
                to="companies.company",
            ),
        ),
        migrations.AddField(
            model_name="subscription",
            name="contract",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="subscriptions",
                to="billing.contract",
            ),
        ),
        migrations.AddField(
            model_name="subscription",
            name="next_billing_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="invoice",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="billing_invoices",
                to="companies.company",
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="contract",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="invoices",
                to="billing.contract",
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="external_reference",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="invoice",
            name="payment_method",
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.RunPython(backfill_billing_plan_fields, migrations.RunPython.noop),
        migrations.RunPython(backfill_subscription_and_invoice_scope, migrations.RunPython.noop),
    ]
