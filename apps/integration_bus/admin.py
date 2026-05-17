from django.contrib import admin

from .models import (
    AutomationTask,
    DeadLetterEvent,
    EventDelivery,
    EventSubscription,
    IntegrationEvent,
    IntegrationLog,
    ReactiveTriggerLog,
    WorkflowDefinition,
    WorkflowExecution,
)


@admin.register(IntegrationEvent)
class IntegrationEventAdmin(admin.ModelAdmin):
    list_display = ("event_name", "priority", "source_module", "event_type", "status", "company", "site", "correlation_id", "occurred_at")
    list_filter = ("priority", "source_module", "event_type", "status", "occurred_at")
    search_fields = ("event_name", "event_key", "aggregate_type", "aggregate_id", "correlation_id", "error_message", "request_id")
    readonly_fields = ("public_id", "published_at", "processed_at", "created_at", "updated_at")


@admin.register(EventSubscription)
class EventSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("event_name", "target_module", "handler_name", "execution_mode", "is_active")
    list_filter = ("target_module", "execution_mode", "is_active")
    search_fields = ("event_name", "target_module", "handler_name")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(WorkflowDefinition)
class WorkflowDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "trigger_event_name", "workflow_type", "is_active", "updated_at")
    list_filter = ("workflow_type", "is_active", "trigger_event_name")
    search_fields = ("name", "slug", "description", "trigger_event_name")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = ("workflow_definition", "integration_event", "status", "started_at", "completed_at")
    list_filter = ("status", "workflow_definition")
    search_fields = ("workflow_definition__name", "integration_event__event_name", "error_message")
    readonly_fields = ("public_id", "started_at", "completed_at", "created_at", "updated_at")
    autocomplete_fields = ("workflow_definition", "integration_event")


@admin.register(AutomationTask)
class AutomationTaskAdmin(admin.ModelAdmin):
    list_display = ("task_name", "task_type", "source_module", "target_module", "status", "scheduled_at")
    list_filter = ("task_type", "source_module", "target_module", "status")
    search_fields = ("task_name", "correlation_id", "error_message")
    readonly_fields = ("public_id", "started_at", "completed_at", "created_at", "updated_at")


@admin.register(IntegrationLog)
class IntegrationLogAdmin(admin.ModelAdmin):
    list_display = ("log_level", "source_module", "target_module", "event_name", "task_name", "created_at")
    list_filter = ("log_level", "source_module", "target_module")
    search_fields = ("message", "event_name", "task_name")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(DeadLetterEvent)
class DeadLetterEventAdmin(admin.ModelAdmin):
    list_display = ("original_event_name", "source_module", "retry_count", "moved_at")
    list_filter = ("source_module", "original_event_name", "moved_at")
    search_fields = ("original_event_name", "failure_reason")
    readonly_fields = ("public_id", "moved_at", "created_at", "updated_at")


@admin.register(EventDelivery)
class EventDeliveryAdmin(admin.ModelAdmin):
    list_display = ("integration_event", "subscriber_name", "delivery_status", "attempt_count", "delivered_at")
    list_filter = ("delivery_status", "subscriber_name")
    search_fields = ("subscriber_name", "last_error", "integration_event__event_name")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(ReactiveTriggerLog)
class ReactiveTriggerLogAdmin(admin.ModelAdmin):
    list_display = ("integration_event", "target_component", "trigger_type", "trigger_status", "created_at")
    list_filter = ("target_component", "trigger_type", "trigger_status")
    search_fields = ("summary", "integration_event__event_name", "target_component")
    readonly_fields = ("public_id", "created_at", "updated_at")
