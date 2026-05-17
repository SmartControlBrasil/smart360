from rest_framework.routers import DefaultRouter

from .views import (
    ArtworkAssetViewSet,
    CreativeStoreProfileViewSet,
    CustomizationRequestViewSet,
    CustomizationTemplateViewSet,
    MarketplaceOrderItemViewSet,
    MarketplaceOrderViewSet,
    MarketplaceProductViewSet,
    MarketplaceVendorViewSet,
    ProductionJobViewSet,
    ProductionStepViewSet,
    ShipmentPreparationViewSet,
)

router = DefaultRouter()
router.register("vendors", MarketplaceVendorViewSet, basename="cdg-vendors")
router.register("products", MarketplaceProductViewSet, basename="cdg-products")
router.register("orders", MarketplaceOrderViewSet, basename="cdg-orders")
router.register("order-items", MarketplaceOrderItemViewSet, basename="cdg-order-items")
router.register("store-profiles", CreativeStoreProfileViewSet, basename="cdg-store-profiles")
router.register("customization-templates", CustomizationTemplateViewSet, basename="cdg-customization-templates")
router.register("customization-requests", CustomizationRequestViewSet, basename="cdg-customization-requests")
router.register("artwork-assets", ArtworkAssetViewSet, basename="cdg-artwork-assets")
router.register("production-jobs", ProductionJobViewSet, basename="cdg-production-jobs")
router.register("production-steps", ProductionStepViewSet, basename="cdg-production-steps")
router.register("shipment-preparations", ShipmentPreparationViewSet, basename="cdg-shipment-preparations")

urlpatterns = router.urls
