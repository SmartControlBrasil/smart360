from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import (
    InAppNotification,
    NotificationBatch,
    NotificationBatchItem,
    NotificationChannel,
    NotificationDeliveryLog,
    NotificationEvent,
    NotificationMessage,
    NotificationPreference,
    NotificationTemplate,
)
from ..services.notification_service import InAppNotificationService, NotificationMessageService
from .serializers import (
    InAppNotificationSerializer,
    NotificationBatchItemSerializer,
    NotificationBatchSerializer,
    NotificationChannelSerializer,
    NotificationDeliveryLogSerializer,
    NotificationEventSerializer,
    NotificationMessageSerializer,
    NotificationPreferenceSerializer,
    NotificationTemplateSerializer,
)


class NotificationBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class NotificationChannelViewSet(NotificationBaseViewSet):
    queryset = NotificationChannel.objects.all()
    serializer_class = NotificationChannelSerializer
    filterset_fields = ("channel_type", "is_active")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "updated_at", "created_at")


class NotificationTemplateViewSet(NotificationBaseViewSet):
    queryset = NotificationTemplate.objects.select_related("channel").all()
    serializer_class = NotificationTemplateSerializer
    filterset_fields = ("channel", "is_active", "template_key")
    search_fields = ("name", "slug", "template_key", "subject_template", "body_template")
    ordering_fields = ("name", "updated_at", "created_at")


class NotificationPreferenceViewSet(NotificationBaseViewSet):
    queryset = NotificationPreference.objects.select_related("user", "company", "channel").all()
    serializer_class = NotificationPreferenceSerializer
    filterset_fields = ("user", "company", "event_key", "channel", "is_enabled")
    search_fields = ("event_key", "user__email", "company__name")
    ordering_fields = ("event_key", "updated_at", "created_at")


class NotificationEventViewSet(NotificationBaseViewSet):
    queryset = NotificationEvent.objects.all()
    serializer_class = NotificationEventSerializer
    filterset_fields = ("event_key", "source_module", "entity_type")
    search_fields = ("event_key", "source_module", "entity_type", "entity_id")
    ordering_fields = ("created_at", "updated_at")


class NotificationMessageViewSet(NotificationBaseViewSet):
    queryset = NotificationMessage.objects.select_related("channel", "template", "recipient_user", "recipient_company").all()
    serializer_class = NotificationMessageSerializer
    filterset_fields = ("event_key", "channel", "template", "recipient_user", "recipient_company", "status")
    search_fields = ("event_key", "recipient_address", "subject_rendered", "body_rendered")
    ordering_fields = ("scheduled_at", "sent_at", "delivered_at", "created_at", "updated_at")

    @action(detail=True, methods=["post"])
    def mark_sent(self, request, pk=None):
        message = self.get_object()
        updated = NotificationMessageService.transition_status(message=message, status=NotificationMessage.Status.SENT)
        return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def mark_delivered(self, request, pk=None):
        message = self.get_object()
        updated = NotificationMessageService.transition_status(message=message, status=NotificationMessage.Status.DELIVERED)
        return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def mark_failed(self, request, pk=None):
        message = self.get_object()
        updated = NotificationMessageService.transition_status(
            message=message,
            status=NotificationMessage.Status.FAILED,
            error_message=request.data.get("error_message", "Notification failed."),
        )
        return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)


class InAppNotificationViewSet(NotificationBaseViewSet):
    queryset = InAppNotification.objects.select_related("user").all()
    serializer_class = InAppNotificationSerializer
    filterset_fields = ("user", "notification_type", "status")
    search_fields = ("user__email", "title", "body", "link_url")
    ordering_fields = ("created_at", "read_at", "updated_at")

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        updated = InAppNotificationService.mark_read(notification=notification)
        return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        notification = self.get_object()
        updated = InAppNotificationService.archive(notification=notification)
        return Response(self.get_serializer(updated).data, status=status.HTTP_200_OK)


class NotificationDeliveryLogViewSet(NotificationBaseViewSet):
    queryset = NotificationDeliveryLog.objects.select_related("notification_message", "channel").all()
    serializer_class = NotificationDeliveryLogSerializer
    filterset_fields = ("notification_message", "channel", "provider_name", "delivery_status")
    search_fields = ("notification_message__event_key", "provider_reference")
    ordering_fields = ("created_at", "updated_at")


class NotificationBatchViewSet(NotificationBaseViewSet):
    queryset = NotificationBatch.objects.all()
    serializer_class = NotificationBatchSerializer
    filterset_fields = ("batch_type", "status")
    search_fields = ("batch_name", "description")
    ordering_fields = ("created_at", "sent_at", "updated_at")


class NotificationBatchItemViewSet(NotificationBaseViewSet):
    queryset = NotificationBatchItem.objects.select_related("batch", "notification_message").all()
    serializer_class = NotificationBatchItemSerializer
    filterset_fields = ("batch", "notification_message", "status")
    search_fields = ("batch__batch_name", "notification_message__event_key")
    ordering_fields = ("created_at", "updated_at")

