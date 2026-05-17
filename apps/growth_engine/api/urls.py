from rest_framework.routers import DefaultRouter

from .views import (
    LeadAssignmentViewSet,
    LeadCampaignViewSet,
    LeadInteractionViewSet,
    LeadQualificationViewSet,
    LeadSourceViewSet,
    LeadTagViewSet,
    LeadViewSet,
)

router = DefaultRouter()
router.register("sources", LeadSourceViewSet, basename="growth-sources")
router.register("tags", LeadTagViewSet, basename="growth-tags")
router.register("campaigns", LeadCampaignViewSet, basename="growth-campaigns")
router.register("leads", LeadViewSet, basename="growth-leads")
router.register("interactions", LeadInteractionViewSet, basename="growth-interactions")
router.register("qualifications", LeadQualificationViewSet, basename="growth-qualifications")
router.register("assignments", LeadAssignmentViewSet, basename="growth-assignments")

urlpatterns = router.urls
