from rest_framework.routers import DefaultRouter

from .views import (
    AutomationTaskViewSet,
    DeadLetterEventViewSet,
    EventDeliveryViewSet,
    EventSubscriptionViewSet,
    IntegrationEventViewSet,
    IntegrationLogViewSet,
    ReactiveTriggerLogViewSet,
    WorkflowDefinitionViewSet,
    WorkflowExecutionViewSet,
)

router = DefaultRouter()
router.register("events", IntegrationEventViewSet, basename="integration-events")
router.register("deliveries", EventDeliveryViewSet, basename="integration-deliveries")
router.register("subscriptions", EventSubscriptionViewSet, basename="integration-subscriptions")
router.register("workflow-definitions", WorkflowDefinitionViewSet, basename="integration-workflow-definitions")
router.register("workflow-executions", WorkflowExecutionViewSet, basename="integration-workflow-executions")
router.register("automation-tasks", AutomationTaskViewSet, basename="integration-automation-tasks")
router.register("logs", IntegrationLogViewSet, basename="integration-logs")
router.register("dead-letters", DeadLetterEventViewSet, basename="integration-dead-letters")
router.register("reactive-triggers", ReactiveTriggerLogViewSet, basename="integration-reactive-triggers")

urlpatterns = router.urls
