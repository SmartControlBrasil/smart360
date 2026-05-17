from django.contrib import admin

from .models import (
    ArtworkAsset,
    CreativeStoreProfile,
    CustomizationRequest,
    CustomizationTemplate,
    ProductionJob,
    ProductionStep,
    ShipmentPreparation,
)


class ProductionStepInline(admin.TabularInline):
    model = ProductionStep
    extra = 0


class ArtworkAssetInline(admin.TabularInline):
    model = ArtworkAsset
    extra = 0


@admin.register(CreativeStoreProfile)
class CreativeStoreProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "vendor", "profile_type", "is_internal_factory", "lead_time_days")
    list_filter = ("profile_type", "is_internal_factory")
    search_fields = ("display_name", "vendor__name", "bio")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("vendor",)


@admin.register(CustomizationTemplate)
class CustomizationTemplateAdmin(admin.ModelAdmin):
    list_display = ("template_name", "product", "allowed_image_upload", "max_images", "is_active")
    list_filter = ("allowed_image_upload", "is_active")
    search_fields = ("template_name", "product__name", "instructions")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("product",)


@admin.register(CustomizationRequest)
class CustomizationRequestAdmin(admin.ModelAdmin):
    list_display = ("order_item", "customization_template", "approval_status", "updated_at")
    list_filter = ("approval_status",)
    search_fields = ("order_item__order__code", "extra_notes", "font_choice", "color_choice")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("order_item", "customization_template")
    inlines = (ArtworkAssetInline,)


@admin.register(ArtworkAsset)
class ArtworkAssetAdmin(admin.ModelAdmin):
    list_display = ("original_name", "customization_request", "asset_type", "status", "updated_at")
    list_filter = ("asset_type", "status")
    search_fields = ("original_name", "customization_request__order_item__order__code")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("customization_request",)


@admin.register(ProductionJob)
class ProductionJobAdmin(admin.ModelAdmin):
    list_display = ("public_id", "order", "order_item", "vendor", "internal_factory", "job_type", "status", "queue_position")
    list_filter = ("job_type", "status")
    search_fields = ("order__code", "order_item__product__name", "vendor__name")
    readonly_fields = ("public_id", "started_at", "completed_at", "created_at", "updated_at")
    autocomplete_fields = ("order", "order_item", "vendor", "internal_factory", "assigned_to")
    inlines = (ProductionStepInline,)


@admin.register(ProductionStep)
class ProductionStepAdmin(admin.ModelAdmin):
    list_display = ("production_job", "step_name", "ordering", "status", "completed_at")
    list_filter = ("status",)
    search_fields = ("production_job__order__code", "step_name", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("production_job",)


@admin.register(ShipmentPreparation)
class ShipmentPreparationAdmin(admin.ModelAdmin):
    list_display = ("order", "shipping_status", "carrier", "tracking_code", "posted_at", "delivered_at")
    list_filter = ("shipping_status",)
    search_fields = ("order__code", "carrier", "tracking_code")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("order",)
