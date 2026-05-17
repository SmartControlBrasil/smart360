from rest_framework.routers import DefaultRouter

from .views import (
    AnalyticalAssignmentViewSet,
    AnalyticalMatchingRecordViewSet,
    AnalyticalProviderViewSet,
    AnalyticalReportViewSet,
    AnalyticalRequestViewSet,
    AnalyticalReviewViewSet,
    AnalyticalServiceCapabilityViewSet,
    AnalyticalServiceCategoryViewSet,
    AnalyticalServiceRegionViewSet,
    AnalyticalServiceViewSet,
)

router = DefaultRouter()
router.register("providers", AnalyticalProviderViewSet, basename="marketplace-analytical-providers")
router.register("service-categories", AnalyticalServiceCategoryViewSet, basename="marketplace-analytical-service-categories")
router.register("services", AnalyticalServiceViewSet, basename="marketplace-analytical-services")
router.register("capabilities", AnalyticalServiceCapabilityViewSet, basename="marketplace-analytical-capabilities")
router.register("service-regions", AnalyticalServiceRegionViewSet, basename="marketplace-analytical-service-regions")
router.register("requests", AnalyticalRequestViewSet, basename="marketplace-analytical-requests")
router.register("matching-records", AnalyticalMatchingRecordViewSet, basename="marketplace-analytical-matching-records")
router.register("assignments", AnalyticalAssignmentViewSet, basename="marketplace-analytical-assignments")
router.register("reports", AnalyticalReportViewSet, basename="marketplace-analytical-reports")
router.register("reviews", AnalyticalReviewViewSet, basename="marketplace-analytical-reviews")

urlpatterns = router.urls
