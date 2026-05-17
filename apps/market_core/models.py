import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class MarketplaceVendor(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        REVIEW = "review", "Review"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="marketplace_vendors",
        null=True,
        blank=True,
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="marketplace_vendors",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    accepts_internal_production = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "market_core_vendors"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class MarketplaceProduct(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    vendor = models.ForeignKey("market_core.MarketplaceVendor", on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    sku = models.CharField(max_length=60, unique=True)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    is_customizable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "market_core_products"
        ordering = ["name"]


class MarketplaceOrder(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        IN_PRODUCTION = "in_production", "In Production"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    code = models.CharField(max_length=40, unique=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="marketplace_orders",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="marketplace_orders",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ordered_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "market_core_orders"
        ordering = ["-ordered_at"]

    def __str__(self) -> str:
        return self.code


class MarketplaceOrderItem(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PERSONALIZATION_PENDING = "personalization_pending", "Personalization Pending"
        IN_PRODUCTION = "in_production", "In Production"
        READY_TO_SHIP = "ready_to_ship", "Ready to Ship"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    order = models.ForeignKey("market_core.MarketplaceOrder", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("market_core.MarketplaceProduct", on_delete=models.PROTECT, related_name="order_items")
    vendor = models.ForeignKey("market_core.MarketplaceVendor", on_delete=models.SET_NULL, related_name="order_items", null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PERSONALIZATION_PENDING)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "market_core_order_items"
        ordering = ["order__ordered_at", "id"]

    def save(self, *args, **kwargs):
        self.total_price = (self.unit_price or Decimal("0.00")) * self.quantity
        if not self.vendor_id:
            self.vendor = self.product.vendor
        super().save(*args, **kwargs)
