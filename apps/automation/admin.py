from django.contrib import admin

from .models import AutomationEvent, AutomationLog, WebhookEndpoint


@admin.register(AutomationLog)
class AutomationLogAdmin(admin.ModelAdmin):
    list_display = ("id", "source", "workflow_name", "event_type", "status", "created_at")
    list_filter = ("status", "source", "event_type", "created_at")
    search_fields = ("source", "workflow_name", "event_type", "error_message")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AutomationEvent)
class AutomationEventAdmin(admin.ModelAdmin):
    list_display = ("id", "event_type", "source", "processed", "processed_at", "created_at")
    list_filter = ("processed", "source", "event_type", "created_at")
    search_fields = ("event_type", "source")
    readonly_fields = ("created_at",)


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "is_active", "created_at", "updated_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("created_at", "updated_at")
