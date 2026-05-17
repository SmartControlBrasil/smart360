from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    PublicAssetViewSet,
    PublicChecklistExecutionViewSet,
    PublicChecklistViewSet,
    PublicCompanyListView,
    PublicApiContextView,
    PublicFailureViewSet,
    PublicMarketplaceAssignmentViewSet,
    PublicMarketplaceOfferViewSet,
    PublicMarketplaceReviewViewSet,
    PublicMarketplaceServiceRequestViewSet,
    PublicMarketplaceTechnicianViewSet,
    PublicPartViewSet,
    PublicPreventiveViewSet,
    PublicReportDetailView,
    PublicReportDownloadView,
    PublicReportListView,
    PublicSiteListView,
    PublicStockMovementViewSet,
    PublicWorkOrderViewSet,
)

app_name = "public-api"

router = DefaultRouter()
router.register("assets", PublicAssetViewSet, basename="public-assets")
router.register("work-orders", PublicWorkOrderViewSet, basename="public-work-orders")
router.register("preventives", PublicPreventiveViewSet, basename="public-preventives")
router.register("failures", PublicFailureViewSet, basename="public-failures")
router.register("checklists", PublicChecklistViewSet, basename="public-checklists")
router.register("checklist-executions", PublicChecklistExecutionViewSet, basename="public-checklist-executions")
router.register("parts", PublicPartViewSet, basename="public-parts")
router.register("stock-movements", PublicStockMovementViewSet, basename="public-stock-movements")
router.register("marketplace/technicians", PublicMarketplaceTechnicianViewSet, basename="public-marketplace-technicians")
router.register("marketplace/service-requests", PublicMarketplaceServiceRequestViewSet, basename="public-marketplace-service-requests")
router.register("marketplace/offers", PublicMarketplaceOfferViewSet, basename="public-marketplace-offers")
router.register("marketplace/assignments", PublicMarketplaceAssignmentViewSet, basename="public-marketplace-assignments")
router.register("marketplace/reviews", PublicMarketplaceReviewViewSet, basename="public-marketplace-reviews")

urlpatterns = router.urls + [
    path("context/", PublicApiContextView.as_view(), name="public-context"),
    path("companies/", PublicCompanyListView.as_view(), name="public-companies"),
    path("sites/", PublicSiteListView.as_view(), name="public-sites"),
    path("reports/", PublicReportListView.as_view(), name="public-reports"),
    path("reports/<slug:report_type>/<uuid:reference_code>/", PublicReportDetailView.as_view(), name="public-report-detail"),
    path("reports/<slug:report_type>/<uuid:reference_code>/download/", PublicReportDownloadView.as_view(), name="public-report-download"),
]
