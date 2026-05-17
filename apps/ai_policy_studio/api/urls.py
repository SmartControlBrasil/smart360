from rest_framework.routers import DefaultRouter

from apps.ai_policy_studio.api.views import (
    PolicyEvaluationViewSet,
    PolicyRuleViewSet,
    PolicyScopeViewSet,
    PolicySimulationRunViewSet,
    PolicyVersionViewSet,
    PolicyViewSet,
)

router = DefaultRouter()
router.register("policies", PolicyViewSet, basename="ai-policy-studio-policy")
router.register("rules", PolicyRuleViewSet, basename="ai-policy-studio-rule")
router.register("scopes", PolicyScopeViewSet, basename="ai-policy-studio-scope")
router.register("versions", PolicyVersionViewSet, basename="ai-policy-studio-version")
router.register("evaluations", PolicyEvaluationViewSet, basename="ai-policy-studio-evaluation")
router.register("simulations", PolicySimulationRunViewSet, basename="ai-policy-studio-simulation")

urlpatterns = router.urls
