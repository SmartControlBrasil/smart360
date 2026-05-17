from rest_framework.routers import DefaultRouter

from .views import (
    CauseReferenceViewSet,
    EquipmentReferenceViewSet,
    EquipmentSymptomMapViewSet,
    FailureActionMapViewSet,
    FailureCauseMapViewSet,
    FailureReferenceViewSet,
    KnowledgeCategoryViewSet,
    KnowledgeFeedbackViewSet,
    KnowledgeLinkRuleViewSet,
    KnowledgeTagViewSet,
    RecommendedActionViewSet,
    SymptomFailureMapViewSet,
    SymptomReferenceViewSet,
    TechnicalDocumentViewSet,
    TroubleshootingArticleViewSet,
)

router = DefaultRouter()
router.register("categories", KnowledgeCategoryViewSet, basename="knowledge-categories")
router.register("equipments", EquipmentReferenceViewSet, basename="knowledge-equipments")
router.register("symptoms", SymptomReferenceViewSet, basename="knowledge-symptoms")
router.register("failures", FailureReferenceViewSet, basename="knowledge-failures")
router.register("causes", CauseReferenceViewSet, basename="knowledge-causes")
router.register("recommended-actions", RecommendedActionViewSet, basename="knowledge-recommended-actions")
router.register("troubleshooting-articles", TroubleshootingArticleViewSet, basename="knowledge-troubleshooting-articles")
router.register("technical-documents", TechnicalDocumentViewSet, basename="knowledge-technical-documents")
router.register("tags", KnowledgeTagViewSet, basename="knowledge-tags")
router.register("link-rules", KnowledgeLinkRuleViewSet, basename="knowledge-link-rules")
router.register("equipment-symptom-maps", EquipmentSymptomMapViewSet, basename="knowledge-equipment-symptom-maps")
router.register("symptom-failure-maps", SymptomFailureMapViewSet, basename="knowledge-symptom-failure-maps")
router.register("failure-cause-maps", FailureCauseMapViewSet, basename="knowledge-failure-cause-maps")
router.register("failure-action-maps", FailureActionMapViewSet, basename="knowledge-failure-action-maps")
router.register("feedback", KnowledgeFeedbackViewSet, basename="knowledge-feedback")

urlpatterns = router.urls
