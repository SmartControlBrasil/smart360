from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.ai_automation_center.api.views import (
    AIAnnotationViewSet,
    AIContextProfileViewSet,
    AIAutomationHistoryView,
    AIGeneratedArtifactViewSet,
    AIModelConfigViewSet,
    AIRunTaskView,
    AITaskExecutionViewSet,
    AITaskHistoryView,
    AITaskRequestViewSet,
    AITaskTypeViewSet,
    AIPromptPreviewView,
    AutomationExecutionViewSet,
    AutomationRuleViewSet,
    PromptTemplateViewSet,
    PromptVersionViewSet,
    RetrievalSourceConfigViewSet,
)

router = DefaultRouter()
router.register("task-types", AITaskTypeViewSet, basename="ai-task-types")
router.register("prompt-templates", PromptTemplateViewSet, basename="ai-prompt-templates")
router.register("prompt-versions", PromptVersionViewSet, basename="ai-prompt-versions")
router.register("context-profiles", AIContextProfileViewSet, basename="ai-context-profiles")
router.register("task-requests", AITaskRequestViewSet, basename="ai-task-requests")
router.register("task-executions", AITaskExecutionViewSet, basename="ai-task-executions")
router.register("generated-artifacts", AIGeneratedArtifactViewSet, basename="ai-generated-artifacts")
router.register("automation-rules", AutomationRuleViewSet, basename="ai-automation-rules")
router.register("automation-executions", AutomationExecutionViewSet, basename="ai-automation-executions")
router.register("annotations", AIAnnotationViewSet, basename="ai-annotations")
router.register("retrieval-source-configs", RetrievalSourceConfigViewSet, basename="ai-retrieval-source-configs")
router.register("model-configs", AIModelConfigViewSet, basename="ai-model-configs")

urlpatterns = router.urls + [
    path("run-task/", AIRunTaskView.as_view(), name="ai-run-task"),
    path("task-history/", AITaskHistoryView.as_view(), name="ai-task-history"),
    path("automation-history/", AIAutomationHistoryView.as_view(), name="ai-automation-history"),
    path("prompt-preview/", AIPromptPreviewView.as_view(), name="ai-prompt-preview"),
]

