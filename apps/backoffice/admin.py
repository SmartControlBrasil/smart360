from django.contrib import admin

from .models import (
    BackofficeAlert,
    BackofficeNote,
    BackofficeTask,
    BackofficeWidget,
    BackofficeQueue,
    BackofficeQueueItem,
    BackofficeQuickAction,
)


@admin.register(BackofficeQueue)
class BackofficeQueueAdmin(admin.ModelAdmin):
    list_display = ("name", "queue_type", "source_module", "is_active", "ordering")
    list_filter = ("queue_type", "source_module", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(BackofficeQueueItem)
class BackofficeQueueItemAdmin(admin.ModelAdmin):
    list_display = ("reference_label", "queue", "status", "priority", "assigned_to", "due_at")
    list_filter = ("queue", "status", "priority")
    search_fields = ("reference_label", "item_type", "item_id")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("queue", "assigned_to")


@admin.register(BackofficeAlert)
class BackofficeAlertAdmin(admin.ModelAdmin):
    list_display = ("title", "alert_type", "source_module", "severity", "status", "created_at", "resolved_at")
    list_filter = ("alert_type", "source_module", "severity", "status")
    search_fields = ("title", "slug", "summary", "details", "related_item_type", "related_item_id")
    readonly_fields = ("public_id", "created_at", "resolved_at", "updated_at")


@admin.register(BackofficeTask)
class BackofficeTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "task_type", "source_module", "assigned_to", "status", "priority", "due_at")
    list_filter = ("task_type", "source_module", "status", "priority")
    search_fields = ("title", "related_item_type", "related_item_id", "notes")
    readonly_fields = ("public_id", "created_at", "completed_at", "updated_at")
    autocomplete_fields = ("assigned_to",)


@admin.register(BackofficeQuickAction)
class BackofficeQuickActionAdmin(admin.ModelAdmin):
    list_display = ("label", "target_module", "action_type", "is_active", "ordering")
    list_filter = ("target_module", "action_type", "is_active")
    search_fields = ("name", "slug", "label", "route_path")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(BackofficeWidget)
class BackofficeWidgetAdmin(admin.ModelAdmin):
    list_display = ("title", "widget_type", "source_module", "is_active", "ordering")
    list_filter = ("widget_type", "source_module", "is_active")
    search_fields = ("name", "slug", "title")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(BackofficeNote)
class BackofficeNoteAdmin(admin.ModelAdmin):
    list_display = ("note_type", "related_item_type", "related_item_id", "created_by", "is_private", "created_at")
    list_filter = ("note_type", "is_private")
    search_fields = ("related_item_type", "related_item_id", "content")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("created_by",)

