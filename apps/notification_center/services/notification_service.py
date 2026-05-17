from collections import defaultdict

from django.db import transaction
from django.utils import timezone

from ..models import (
    InAppNotification,
    NotificationDeliveryLog,
    NotificationEvent,
    NotificationMessage,
    NotificationPreference,
    NotificationTemplate,
)


class SafeFormatDict(defaultdict):
    def __missing__(self, key):
        return "{" + key + "}"


class TemplateRenderService:
    @staticmethod
    def render(*, template, payload):
        context = SafeFormatDict(str, payload or {})
        subject = template.subject_template.format_map(context) if template.subject_template else ""
        body = template.body_template.format_map(context)
        return subject, body


class NotificationPreferenceService:
    @staticmethod
    def is_enabled(*, event_key, channel, user=None, company=None):
        if user:
            preference = NotificationPreference.objects.filter(
                user=user,
                event_key=event_key,
                channel=channel,
            ).first()
            if preference is not None:
                return preference.is_enabled
        if company:
            preference = NotificationPreference.objects.filter(
                company=company,
                event_key=event_key,
                channel=channel,
            ).first()
            if preference is not None:
                return preference.is_enabled
        return True


class NotificationEventService:
    @staticmethod
    def record_event(**validated_data):
        return NotificationEvent.objects.create(**validated_data)


class NotificationMessageService:
    @staticmethod
    @transaction.atomic
    def create_message(**validated_data):
        template = validated_data.get("template")
        payload = validated_data.get("payload", {})
        channel = validated_data["channel"]
        recipient_user = validated_data.get("recipient_user")
        recipient_company = validated_data.get("recipient_company")

        if not NotificationPreferenceService.is_enabled(
            event_key=validated_data["event_key"],
            channel=channel,
            user=recipient_user,
            company=recipient_company,
        ):
            validated_data["status"] = NotificationMessage.Status.CANCELLED

        if template:
            subject, body = TemplateRenderService.render(template=template, payload=payload)
            validated_data.setdefault("subject_rendered", subject)
            validated_data.setdefault("body_rendered", body)

        message = NotificationMessage.objects.create(**validated_data)
        NotificationDeliveryLog.objects.create(
            notification_message=message,
            channel=message.channel,
            delivery_status=NotificationDeliveryLog.DeliveryStatus.PENDING,
            response_payload={},
        )
        return message

    @staticmethod
    def transition_status(*, message, status, error_message=""):
        now = timezone.now()
        message.status = status
        if status == NotificationMessage.Status.SENT and message.sent_at is None:
            message.sent_at = now
        if status == NotificationMessage.Status.DELIVERED and message.delivered_at is None:
            message.delivered_at = now
        if status == NotificationMessage.Status.FAILED and message.failed_at is None:
            message.failed_at = now
            message.error_message = error_message
        if status != NotificationMessage.Status.FAILED:
            message.error_message = ""
        message.save()

        latest_log = message.delivery_logs.order_by("-created_at").first()
        if latest_log:
            mapping = {
                NotificationMessage.Status.SENT: NotificationDeliveryLog.DeliveryStatus.SENT,
                NotificationMessage.Status.DELIVERED: NotificationDeliveryLog.DeliveryStatus.DELIVERED,
                NotificationMessage.Status.FAILED: NotificationDeliveryLog.DeliveryStatus.FAILED,
                NotificationMessage.Status.CANCELLED: NotificationDeliveryLog.DeliveryStatus.FAILED,
            }
            if status in mapping:
                latest_log.delivery_status = mapping[status]
                latest_log.response_payload = {"message_status": status, "error_message": error_message}
                latest_log.save(update_fields=["delivery_status", "response_payload", "updated_at"])
        return message


class InAppNotificationService:
    @staticmethod
    def create_notification(**validated_data):
        return InAppNotification.objects.create(**validated_data)

    @staticmethod
    def mark_read(*, notification):
        notification.status = InAppNotification.Status.READ
        notification.read_at = notification.read_at or timezone.now()
        notification.save(update_fields=["status", "read_at", "updated_at"])
        return notification

    @staticmethod
    def archive(*, notification):
        notification.status = InAppNotification.Status.ARCHIVED
        if notification.read_at is None:
            notification.read_at = timezone.now()
        notification.save(update_fields=["status", "read_at", "updated_at"])
        return notification

