from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

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
from .serializers import (
    ArtworkAssetSerializer,
    CreativeStoreProfileSerializer,
    CustomizationRequestSerializer,
    CustomizationTemplateSerializer,
    MarketplaceOrderItemSerializer,
    MarketplaceOrderSerializer,
    MarketplaceProductSerializer,
    MarketplaceVendorSerializer,
    ProductionJobSerializer,
    ProductionStepSerializer,
    ShipmentPreparationSerializer,
)


class CanecaBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class MarketplaceVendorViewSet(CanecaBaseViewSet):
    queryset = MarketplaceVendor.objects.select_related("company", "owner").all()
    serializer_class = MarketplaceVendorSerializer
    filterset_fields = ("status", "accepts_internal_production")
    search_fields = ("name", "slug")
    ordering_fields = ("name", "updated_at")


class MarketplaceProductViewSet(CanecaBaseViewSet):
    queryset = MarketplaceProduct.objects.select_related("vendor").all()
    serializer_class = MarketplaceProductSerializer
    filterset_fields = ("vendor", "is_customizable", "is_active")
    search_fields = ("name", "slug", "sku")
    ordering_fields = ("name", "base_price", "updated_at")


class MarketplaceOrderViewSet(CanecaBaseViewSet):
    queryset = MarketplaceOrder.objects.select_related("customer", "company").prefetch_related("items").all()
    serializer_class = MarketplaceOrderSerializer
    filterset_fields = ("status", "customer", "company")
    search_fields = ("code", "customer__email")
    ordering_fields = ("ordered_at", "total_amount", "updated_at")


class MarketplaceOrderItemViewSet(CanecaBaseViewSet):
    queryset = MarketplaceOrderItem.objects.select_related("order", "product", "vendor").all()
    serializer_class = MarketplaceOrderItemSerializer
    filterset_fields = ("order", "product", "vendor", "status")
    search_fields = ("order__code", "product__name")
    ordering_fields = ("created_at", "total_price", "updated_at")


class CreativeStoreProfileViewSet(CanecaBaseViewSet):
    queryset = CreativeStoreProfile.objects.select_related("vendor").all()
    serializer_class = CreativeStoreProfileSerializer
    filterset_fields = ("profile_type", "is_internal_factory")
    search_fields = ("display_name", "vendor__name", "bio")
    ordering_fields = ("display_name", "lead_time_days", "updated_at")


class CustomizationTemplateViewSet(CanecaBaseViewSet):
    queryset = CustomizationTemplate.objects.select_related("product", "product__vendor").all()
    serializer_class = CustomizationTemplateSerializer
    filterset_fields = ("product", "is_active", "allowed_image_upload")
    search_fields = ("template_name", "instructions")
    ordering_fields = ("template_name", "updated_at")


class CustomizationRequestViewSet(CanecaBaseViewSet):
    queryset = CustomizationRequest.objects.select_related("order_item", "customization_template").prefetch_related("artwork_assets").all()
    serializer_class = CustomizationRequestSerializer
    filterset_fields = ("order_item", "approval_status", "customization_template")
    search_fields = ("order_item__order__code", "font_choice", "color_choice", "extra_notes")
    ordering_fields = ("created_at", "updated_at")


class ArtworkAssetViewSet(CanecaBaseViewSet):
    queryset = ArtworkAsset.objects.select_related("customization_request").all()
    serializer_class = ArtworkAssetSerializer
    filterset_fields = ("customization_request", "asset_type", "status")
    search_fields = ("original_name",)
    ordering_fields = ("created_at", "updated_at")


class ProductionJobViewSet(CanecaBaseViewSet):
    queryset = ProductionJob.objects.select_related("order", "order_item", "vendor", "internal_factory", "assigned_to").prefetch_related("steps").all()
    serializer_class = ProductionJobSerializer
    filterset_fields = ("order", "order_item", "vendor", "internal_factory", "job_type", "status")
    search_fields = ("order__code", "notes")
    ordering_fields = ("queue_position", "due_date", "updated_at")

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        job = self.get_object()
        ProductionJobService.start_job(job=job)
        return Response(self.get_serializer(job).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        job = self.get_object()
        ProductionJobService.complete_job(job=job)
        return Response(self.get_serializer(job).data)


class ProductionStepViewSet(CanecaBaseViewSet):
    queryset = ProductionStep.objects.select_related("production_job").all()
    serializer_class = ProductionStepSerializer
    filterset_fields = ("production_job", "status")
    search_fields = ("step_name", "notes")
    ordering_fields = ("ordering", "updated_at")


class ShipmentPreparationViewSet(CanecaBaseViewSet):
    queryset = ShipmentPreparation.objects.select_related("order").all()
    serializer_class = ShipmentPreparationSerializer
    filterset_fields = ("order", "shipping_status")
    search_fields = ("carrier", "tracking_code", "order__code")
    ordering_fields = ("posted_at", "delivered_at", "updated_at")

    @action(detail=True, methods=["post"])
    def mark_posted(self, request, pk=None):
        shipment = self.get_object()
        ShipmentService.mark_posted(shipment=shipment)
        return Response(self.get_serializer(shipment).data)
