from rest_framework.routers import DefaultRouter

from apps.ai_autonomous_ops.api.views import (
    AutonomousExecutionGuardViewSet,
    AutonomousExecutionViewSet,
    AutonomousIncidentViewSet,
    AutonomousModeConfigViewSet,
)

router = DefaultRouter()
router.register("configs", AutonomousModeConfigViewSet, basename="ai-autonomy-config")
router.register("executions", AutonomousExecutionViewSet, basename="ai-autonomy-execution")
router.register("incidents", AutonomousIncidentViewSet, basename="ai-autonomy-incident")
router.register("guards", AutonomousExecutionGuardViewSet, basename="ai-autonomy-guard")

urlpatterns = router.urls

