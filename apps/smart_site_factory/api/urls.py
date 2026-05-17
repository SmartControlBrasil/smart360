from rest_framework.routers import DefaultRouter

from .views import (
    ConfiguratorOptionViewSet,
    ConfiguratorQuestionViewSet,
    DeliveryRecordViewSet,
    NicheViewSet,
    ProductionTaskViewSet,
    SiteOrderViewSet,
    SiteProjectIntakeViewSet,
    TemplateRecommendationRuleViewSet,
    TemplateViewSet,
)

router = DefaultRouter()
router.register("niches", NicheViewSet, basename="ssf-niches")
router.register("templates", TemplateViewSet, basename="ssf-templates")
router.register("questions", ConfiguratorQuestionViewSet, basename="ssf-questions")
router.register("options", ConfiguratorOptionViewSet, basename="ssf-options")
router.register("rules", TemplateRecommendationRuleViewSet, basename="ssf-rules")
router.register("orders", SiteOrderViewSet, basename="ssf-orders")
router.register("intakes", SiteProjectIntakeViewSet, basename="ssf-intakes")
router.register("production", ProductionTaskViewSet, basename="ssf-production")
router.register("deliveries", DeliveryRecordViewSet, basename="ssf-deliveries")

urlpatterns = router.urls
