from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.ai_optimization_loop.api.views import (
    AgentQualityView,
    CopilotQualityView,
    DecisionOutcomeViewSet,
    FeedbackSignalViewSet,
    OptimizationPolicyViewSet,
    OptimizationProposalViewSet,
    RecommendationOutcomeViewSet,
    SimulationOutcomeViewSet,
)

router = DefaultRouter()
router.register("feedbacks", FeedbackSignalViewSet, basename="ai-optimization-feedback")
router.register("recommendation-outcomes", RecommendationOutcomeViewSet, basename="ai-optimization-recommendation-outcome")
router.register("decision-outcomes", DecisionOutcomeViewSet, basename="ai-optimization-decision-outcome")
router.register("simulation-outcomes", SimulationOutcomeViewSet, basename="ai-optimization-simulation-outcome")
router.register("proposals", OptimizationProposalViewSet, basename="ai-optimization-proposal")
router.register("policies", OptimizationPolicyViewSet, basename="ai-optimization-policy")

urlpatterns = router.urls + [
    path("quality/agents/", AgentQualityView.as_view(), name="ai-optimization-agent-quality"),
    path("quality/copilots/", CopilotQualityView.as_view(), name="ai-optimization-copilot-quality"),
]
