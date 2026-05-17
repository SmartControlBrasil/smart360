from django.contrib import admin

from .models import MarketplaceOrder, MarketplaceOrderItem, MarketplaceProduct, MarketplaceVendor


class MarketplaceOrderItemInline(admin.TabularInline):
    model = MarketplaceOrderItem
    extra = 0
    autocomplete_fields = ("product", "vendor")


@admin.register(MarketplaceVendor)
class MarketplaceVendorAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "owner", "company", "accepts_internal_production")
    list_filter = ("status", "accepts_internal_production")
    search_fields = ("name", "slug", "owner__email", "company__name")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("owner", "company")


@admin.register(MarketplaceProduct)
class MarketplaceProductAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "sku", "base_price", "is_customizable", "is_active")
    list_filter = ("vendor", "is_customizable", "is_active")
    search_fields = ("name", "slug", "sku")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("vendor",)


@admin.register(MarketplaceOrder)
class MarketplaceOrderAdmin(admin.ModelAdmin):
    list_display = ("code", "customer", "status", "total_amount", "ordered_at")
    list_filter = ("status",)
    search_fields = ("code", "customer__email", "company__name")
    readonly_fields = ("public_id", "ordered_at", "created_at", "updated_at")
    autocomplete_fields = ("customer", "company")
    inlines = (MarketplaceOrderItemInline,)


@admin.register(MarketplaceOrderItem)
class MarketplaceOrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "vendor", "quantity", "status", "total_price")
    list_filter = ("status", "vendor")
    search_fields = ("order__code", "product__name", "vendor__name")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("order", "product", "vendor")
