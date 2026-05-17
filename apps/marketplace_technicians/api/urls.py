from rest_framework.routers import DefaultRouter

from .views import (
    ServiceRegionViewSet,
    TechnicianAssignmentViewSet,
    TechnicianAvailabilityViewSet,
    TechnicianCompensationRecordViewSet,
    TechnicianMatchingRecordViewSet,
    TechnicianPortfolioItemViewSet,
    TechnicianProfileViewSet,
    TechnicianReviewViewSet,
    TechnicianServiceOfferViewSet,
    TechnicianServiceRegionViewSet,
    TechnicianServiceRequestViewSet,
    TechnicianSkillAssignmentViewSet,
    TechnicianSkillViewSet,
    TechnicianWorkReportViewSet,
)

router = DefaultRouter()
router.register("technician-profiles", TechnicianProfileViewSet, basename="marketplace-technicians-profiles")
router.register("skills", TechnicianSkillViewSet, basename="marketplace-technicians-skills")
router.register("skill-assignments", TechnicianSkillAssignmentViewSet, basename="marketplace-technicians-skill-assignments")
router.register("service-regions", ServiceRegionViewSet, basename="marketplace-technicians-service-regions")
router.register("technician-service-regions", TechnicianServiceRegionViewSet, basename="marketplace-technicians-technician-service-regions")
router.register("availability", TechnicianAvailabilityViewSet, basename="marketplace-technicians-availability")
router.register("portfolio", TechnicianPortfolioItemViewSet, basename="marketplace-technicians-portfolio")
router.register("service-requests", TechnicianServiceRequestViewSet, basename="marketplace-technicians-service-requests")
router.register("service-offers", TechnicianServiceOfferViewSet, basename="marketplace-technicians-service-offers")
router.register("matching-records", TechnicianMatchingRecordViewSet, basename="marketplace-technicians-matching-records")
router.register("assignments", TechnicianAssignmentViewSet, basename="marketplace-technicians-assignments")
router.register("work-reports", TechnicianWorkReportViewSet, basename="marketplace-technicians-work-reports")
router.register("reviews", TechnicianReviewViewSet, basename="marketplace-technicians-reviews")
router.register("compensation-records", TechnicianCompensationRecordViewSet, basename="marketplace-technicians-compensations")

urlpatterns = router.urls
