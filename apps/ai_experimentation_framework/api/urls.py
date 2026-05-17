from rest_framework.routers import DefaultRouter

from apps.ai_experimentation_framework.api.views import ExperimentAssignmentViewSet, ExperimentViewSet

router = DefaultRouter()
router.register("experiments", ExperimentViewSet, basename="ai-experiment")
router.register("assignments", ExperimentAssignmentViewSet, basename="ai-experiment-assignment")

urlpatterns = router.urls

