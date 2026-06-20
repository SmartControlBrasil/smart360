from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.ai_agents_center.api.views import (
    AIBriefingGenerateView,
    AIBriefingViewedView,
    AIBriefingViewSet,
    AgentActionProposalViewSet,
    AgentAnomalyAttentionFlagViewSet,
    AgentAssetAttentionFlagViewSet,
    AgentDefinitionViewSet,
    AgentMarketplaceRequestFlagViewSet,
    AgentManualRunView,
    AgentMemoryEntryViewSet,
    AgentProfitabilityAttentionFlagViewSet,
    AgentRecommendationViewSet,
    AgentRunViewSet,
    AgentScheduleHealthFlagViewSet,
    CommercialOpportunityViewSet,
    AtlasProspectImportView,
    AnomalyAnalysisRunView,
    MaintenanceAnalysisRunView,
    ManagerCopilotContextView,
    ManagerCopilotProposalApproveView,
    ManagerCopilotProposalRejectView,
    ManagerCopilotQueryView,
    ManagerCopilotRecommendationsView,
    ManagerCopilotSessionViewSet,
    ManagerCopilotSuggestionsView,
    MarketplaceAnalysisRunView,
    ProfitabilityAnalysisRunView,
    SchedulingAnalysisRunView,
)

router = DefaultRouter()
router.register("agents", AgentDefinitionViewSet, basename="ai-agents")
router.register("runs", AgentRunViewSet, basename="ai-agent-runs")
router.register("recommendations", AgentRecommendationViewSet, basename="ai-agent-recommendations")
router.register("action-proposals", AgentActionProposalViewSet, basename="ai-agent-action-proposals")
router.register("memory", AgentMemoryEntryViewSet, basename="ai-agent-memory")
router.register("maintenance-attention-assets", AgentAssetAttentionFlagViewSet, basename="ai-agent-maintenance-attention-assets")
router.register("scheduling-health", AgentScheduleHealthFlagViewSet, basename="ai-agent-scheduling-health")
router.register("profitability-health", AgentProfitabilityAttentionFlagViewSet, basename="ai-agent-profitability-health")
router.register("marketplace-health", AgentMarketplaceRequestFlagViewSet, basename="ai-agent-marketplace-health")
router.register("anomaly-health", AgentAnomalyAttentionFlagViewSet, basename="ai-agent-anomaly-health")
router.register("copilot/sessions", ManagerCopilotSessionViewSet, basename="ai-agent-copilot-sessions")
router.register("briefings", AIBriefingViewSet, basename="ai-agent-briefings")
router.register("commercial-opportunities", CommercialOpportunityViewSet, basename="ai-agent-commercial-opportunities")

urlpatterns = [
    path("atlas/import-prospects/", AtlasProspectImportView.as_view(), name="ai-agent-atlas-import-prospects"),
    path("manual-run/", AgentManualRunView.as_view(), name="ai-agent-manual-run"),
    path("maintenance/run/", MaintenanceAnalysisRunView.as_view(), name="ai-agent-maintenance-run"),
    path("scheduling/run/", SchedulingAnalysisRunView.as_view(), name="ai-agent-scheduling-run"),
    path("profitability/run/", ProfitabilityAnalysisRunView.as_view(), name="ai-agent-profitability-run"),
    path("marketplace/run/", MarketplaceAnalysisRunView.as_view(), name="ai-agent-marketplace-run"),
    path("anomaly/run/", AnomalyAnalysisRunView.as_view(), name="ai-agent-anomaly-run"),
    path("briefings/generate/", AIBriefingGenerateView.as_view(), name="ai-agent-briefing-generate"),
    path("briefings/<uuid:briefing_public_id>/viewed/", AIBriefingViewedView.as_view(), name="ai-agent-briefing-viewed"),
    path("copilot/query/", ManagerCopilotQueryView.as_view(), name="ai-agent-copilot-query"),
    path("copilot/context/", ManagerCopilotContextView.as_view(), name="ai-agent-copilot-context"),
    path("copilot/suggestions/", ManagerCopilotSuggestionsView.as_view(), name="ai-agent-copilot-suggestions"),
    path("copilot/recommendations/", ManagerCopilotRecommendationsView.as_view(), name="ai-agent-copilot-recommendations"),
    path(
        "copilot/proposals/<uuid:proposal_public_id>/approve/",
        ManagerCopilotProposalApproveView.as_view(),
        name="ai-agent-copilot-proposal-approve",
    ),
    path(
        "copilot/proposals/<uuid:proposal_public_id>/reject/",
        ManagerCopilotProposalRejectView.as_view(),
        name="ai-agent-copilot-proposal-reject",
    ),
] + router.urls
