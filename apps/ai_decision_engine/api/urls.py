from rest_framework.routers import DefaultRouter
from apps.ai_decision_engine.api.views import (
    AgentDecisionViewSet,
    DecisionExecutionViewSet,
    DecisionPolicyViewSet
)

router = DefaultRouter()

router.register("decisions", AgentDecisionViewSet, basename="ai-decision")
router.register("executions", DecisionExecutionViewSet, basename="ai-decision-execution")
router.register("policies", DecisionPolicyViewSet, basename="ai-decision-policy")

urlpatterns = router.urls