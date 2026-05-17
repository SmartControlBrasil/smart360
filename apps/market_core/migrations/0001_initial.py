import decimal
import django.db.models.deletion
import django.utils.timezone
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("companies", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MarketplaceVendor",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("slug", models.SlugField(max_length=180, unique=True)),
                ("status", models.CharField(choices=[("active", "Active"), ("inactive", "Inactive"), ("review", "Review")], default="active", max_length=20)),
                ("accepts_internal_production", models.BooleanField(default=False)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="marketplace_vendors", to="companies.company")),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="marketplace_vendors", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "market_core_vendors", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="MarketplaceProduct",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("slug", models.SlugField(max_length=180, unique=True)),
                ("sku", models.CharField(max_length=60, unique=True)),
                ("description", models.TextField(blank=True)),
                ("base_price", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=10)),
                ("is_customizable", models.BooleanField(default=True)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("vendor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="products", to="market_core.marketplacevendor")),
            ],
            options={"db_table": "market_core_products", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="MarketplaceOrder",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("code", models.CharField(max_length=40, unique=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("paid", "Paid"), ("in_production", "In Production"), ("shipped", "Shipped"), ("delivered", "Delivered"), ("cancelled", "Cancelled")], default="pending", max_length=20)),
                ("total_amount", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=10)),
                ("notes", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("ordered_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="marketplace_orders", to="companies.company")),
                ("customer", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="marketplace_orders", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "market_core_orders", "ordering": ["-ordered_at"]},
        ),
        migrations.CreateModel(
            name="MarketplaceOrderItem",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("unit_price", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=10)),
                ("total_price", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=10)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("personalization_pending", "Personalization Pending"), ("in_production", "In Production"), ("ready_to_ship", "Ready to Ship"), ("shipped", "Shipped"), ("delivered", "Delivered")], default="personalization_pending", max_length=30)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="market_core.marketplaceorder")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="order_items", to="market_core.marketplaceproduct")),
                ("vendor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="order_items", to="market_core.marketplacevendor")),
            ],
            options={"db_table": "market_core_order_items", "ordering": ["order__ordered_at", "id"]},
        ),
    ]
