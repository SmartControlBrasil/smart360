from rest_framework import serializers

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
from ..services.notification_service import (
    InAppNotificationService,
    NotificationEventService,
    NotificationMessageService,
)


class NotificationChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationChannel
        fields = ("id", "public_id", "name", "slug", "channel_type", "description", "is_active", "config_json", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = (
            "id",
            "public_id",
            "name",
            "slug",
            "channel",
            "template_key",
            "subject_template",
            "body_template",
            "description",
            "is_active",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ("id", "public_id", "user", "company", "event_key", "channel", "is_enabled", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class NotificationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationEvent
        fields = ("id", "public_id", "event_key", "source_module", "entity_type", "entity_id", "payload", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "updated_at")

    def create(self, validated_data):
        return NotificationEventService.record_event(**validated_data)


class NotificationMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationMessage
        fields = (
            "id",
            "public_id",
            "event_key",
            "channel",
            "template",
            "recipient_user",
            "recipient_company",
            "recipient_address",
            "subject_rendered",
            "body_rendered",
            "payload",
            "status",
            "scheduled_at",
            "sent_at",
            "delivered_at",
            "failed_at",
            "error_message",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "sent_at", "delivered_at", "failed_at", "created_at", "updated_at")

    def create(self, validated_data):
        return NotificationMessageService.create_message(**validated_data)


class InAppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InAppNotification
        fields = ("id", "public_id", "user", "title", "body", "link_url", "notification_type", "status", "read_at", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "read_at", "created_at", "updated_at")

    def create(self, validated_data):
        return InAppNotificationService.create_notification(**validated_data)


class NotificationDeliveryLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationDeliveryLog
        fields = ("id", "public_id", "notification_message", "channel", "provider_name", "provider_reference", "delivery_status", "response_payload", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class NotificationBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationBatch
        fields = ("id", "public_id", "batch_name", "batch_type", "description", "status", "created_at", "sent_at", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "sent_at", "updated_at")


class NotificationBatchItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationBatchItem
        fields = ("id", "public_id", "batch", "notification_message", "status", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "updated_at")

