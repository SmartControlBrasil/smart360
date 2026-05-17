from django.contrib import admin

from .models import (
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


class NotificationBatchItemInline(admin.TabularInline):
    model = NotificationBatchItem
    extra = 0
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ("name", "channel_type", "is_active", "updated_at")
    list_filter = ("channel_type", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "channel", "template_key", "is_active", "updated_at")
    list_filter = ("channel", "is_active")
    search_fields = ("name", "slug", "template_key", "subject_template", "body_template")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("channel",)


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("event_key", "channel", "user", "company", "is_enabled")
    list_filter = ("channel", "is_enabled", "event_key")
    search_fields = ("event_key", "user__email", "company__name")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("user", "company", "channel")


@admin.register(NotificationEvent)
class NotificationEventAdmin(admin.ModelAdmin):
    list_display = ("event_key", "source_module", "entity_type", "entity_id", "created_at")
    list_filter = ("source_module", "event_key")
    search_fields = ("event_key", "source_module", "entity_type", "entity_id")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(NotificationMessage)
class NotificationMessageAdmin(admin.ModelAdmin):
    list_display = ("event_key", "channel", "recipient_user", "recipient_company", "status", "created_at")
    list_filter = ("channel", "status", "event_key")
    search_fields = ("event_key", "recipient_address", "subject_rendered", "body_rendered")
    readonly_fields = ("public_id", "sent_at", "delivered_at", "failed_at", "created_at", "updated_at")
    autocomplete_fields = ("channel", "template", "recipient_user", "recipient_company")


@admin.register(InAppNotification)
class InAppNotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "notification_type", "status", "created_at")
    list_filter = ("notification_type", "status")
    search_fields = ("user__email", "title", "body", "link_url")
    readonly_fields = ("public_id", "read_at", "created_at", "updated_at")
    autocomplete_fields = ("user",)


@admin.register(NotificationDeliveryLog)
class NotificationDeliveryLogAdmin(admin.ModelAdmin):
    list_display = ("notification_message", "channel", "provider_name", "delivery_status", "created_at")
    list_filter = ("channel", "delivery_status", "provider_name")
    search_fields = ("notification_message__event_key", "provider_reference")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("notification_message", "channel")


@admin.register(NotificationBatch)
class NotificationBatchAdmin(admin.ModelAdmin):
    list_display = ("batch_name", "batch_type", "status", "created_at", "sent_at")
    list_filter = ("batch_type", "status")
    search_fields = ("batch_name", "description")
    readonly_fields = ("public_id", "sent_at", "created_at", "updated_at")
    inlines = (NotificationBatchItemInline,)


@admin.register(NotificationBatchItem)
class NotificationBatchItemAdmin(admin.ModelAdmin):
    list_display = ("batch", "notification_message", "status", "created_at")
    list_filter = ("status", "batch")
    search_fields = ("batch__batch_name", "notification_message__event_key")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("batch", "notification_message")

