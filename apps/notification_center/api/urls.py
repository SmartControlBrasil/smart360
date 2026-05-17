from rest_framework.routers import DefaultRouter

from .views import (
    InAppNotificationViewSet,
    NotificationBatchItemViewSet,
    NotificationBatchViewSet,
    NotificationChannelViewSet,
    NotificationDeliveryLogViewSet,
    NotificationEventViewSet,
    NotificationMessageViewSet,
    NotificationPreferenceViewSet,
    NotificationTemplateViewSet,
)

router = DefaultRouter()
router.register("channels", NotificationChannelViewSet, basename="notification-channels")
router.register("templates", NotificationTemplateViewSet, basename="notification-templates")
router.register("preferences", NotificationPreferenceViewSet, basename="notification-preferences")
router.register("events", NotificationEventViewSet, basename="notification-events")
router.register("messages", NotificationMessageViewSet, basename="notification-messages")
router.register("in-app-notifications", InAppNotificationViewSet, basename="notification-in-app-notifications")
router.register("delivery-logs", NotificationDeliveryLogViewSet, basename="notification-delivery-logs")
router.register("batches", NotificationBatchViewSet, basename="notification-batches")
router.register("batch-items", NotificationBatchItemViewSet, basename="notification-batch-items")

urlpatterns = router.urls

