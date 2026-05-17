from rest_framework import serializers

from apps.market_core.models import MarketplaceOrder, MarketplaceOrderItem, MarketplaceProduct, MarketplaceVendor

from ..models import (
    ArtworkAsset,
    CreativeStoreProfile,
    CustomizationRequest,
    CustomizationTemplate,
    ProductionJob,
    ProductionStep,
    ShipmentPreparation,
)
from ..services.production_service import ProductionJobService, ShipmentService


class MarketplaceVendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceVendor
        fields = ("public_id", "company", "owner", "name", "slug", "status", "accepts_internal_production", "metadata", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class MarketplaceProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceProduct
        fields = ("public_id", "vendor", "name", "slug", "sku", "description", "base_price", "is_customizable", "is_active", "metadata", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class MarketplaceOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceOrderItem
        fields = ("public_id", "order", "product", "vendor", "quantity", "unit_price", "total_price", "status", "metadata", "created_at", "updated_at")
        read_only_fields = ("public_id", "total_price", "created_at", "updated_at")


class MarketplaceOrderSerializer(serializers.ModelSerializer):
    items = MarketplaceOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = MarketplaceOrder
        fields = ("public_id", "code", "customer", "company", "status", "total_amount", "notes", "metadata", "ordered_at", "items", "created_at", "updated_at")
        read_only_fields = ("public_id", "ordered_at", "created_at", "updated_at")


class CreativeStoreProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreativeStoreProfile
        fields = ("public_id", "vendor", "display_name", "bio", "profile_type", "production_capabilities", "is_internal_factory", "lead_time_days", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class CustomizationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomizationTemplate
        fields = ("public_id", "product", "template_name", "instructions", "allowed_text_fields", "allowed_image_upload", "max_images", "is_active", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class ArtworkAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtworkAsset
        fields = ("public_id", "customization_request", "file", "asset_type", "original_name", "status", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class CustomizationRequestSerializer(serializers.ModelSerializer):
    artwork_assets = ArtworkAssetSerializer(many=True, read_only=True)

    class Meta:
        model = CustomizationRequest
        fields = (
            "public_id",
            "order_item",
            "customization_template",
            "customer_text",
            "uploaded_assets",
            "font_choice",
            "color_choice",
            "extra_notes",
            "approval_status",
            "artwork_assets",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class ProductionStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductionStep
        fields = ("public_id", "production_job", "step_name", "ordering", "status", "completed_at", "notes", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class ProductionJobSerializer(serializers.ModelSerializer):
    steps = ProductionStepSerializer(many=True, read_only=True)

    class Meta:
        model = ProductionJob
        fields = (
            "public_id",
            "order",
            "order_item",
            "vendor",
            "internal_factory",
            "job_type",
            "status",
            "queue_position",
            "assigned_to",
            "started_at",
            "completed_at",
            "due_date",
            "notes",
            "steps",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def create(self, validated_data):
        return ProductionJobService.create_job(validated_data=validated_data, user=self.context["request"].user)


class ShipmentPreparationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentPreparation
        fields = ("public_id", "order", "shipping_status", "carrier", "tracking_code", "posted_at", "delivered_at", "notes", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")
