from rest_framework import serializers

from ..models import (
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
from ..services.integration_service import (
    AutomationTaskService,
    IntegrationEventService,
    WorkflowService,
)


class IntegrationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationEvent
        fields = (
            "id",
            "public_id",
            "event_name",
            "event_version",
            "event_key",
            "source_module",
            "event_type",
            "company",
            "site",
            "aggregate_type",
            "aggregate_id",
            "payload",
            "metadata",
            "request_id",
            "priority",
            "status",
            "occurred_at",
            "published_at",
            "processed_at",
            "retry_count",
            "error_message",
            "correlation_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "event_key", "published_at", "processed_at", "retry_count", "created_at", "updated_at")

    def create(self, validated_data):
        return IntegrationEventService.record_event(**validated_data)


class EventSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventSubscription
        fields = ("id", "public_id", "event_name", "target_module", "handler_name", "is_active", "execution_mode", "retry_policy", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class WorkflowDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowDefinition
        fields = (
            "id",
            "public_id",
            "name",
            "slug",
            "description",
            "trigger_event_name",
            "workflow_type",
            "config_json",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class WorkflowExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowExecution
        fields = (
            "id",
            "public_id",
            "workflow_definition",
            "integration_event",
            "status",
            "started_at",
            "completed_at",
            "error_message",
            "output_json",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "started_at", "completed_at", "created_at", "updated_at")

    def create(self, validated_data):
        return WorkflowService.create_execution(**validated_data)


class AutomationTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationTask
        fields = (
            "id",
            "public_id",
            "task_name",
            "task_type",
            "source_module",
            "target_module",
            "payload",
            "status",
            "scheduled_at",
            "started_at",
            "completed_at",
            "retry_count",
            "error_message",
            "correlation_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "started_at", "completed_at", "retry_count", "created_at", "updated_at")

    def create(self, validated_data):
        return AutomationTaskService.create_task(**validated_data)


class IntegrationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationLog
        fields = ("id", "public_id", "source_module", "target_module", "event_name", "task_name", "log_level", "message", "payload", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class DeadLetterEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeadLetterEvent
        fields = ("id", "public_id", "original_event_name", "source_module", "payload", "failure_reason", "retry_count", "moved_at", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "moved_at", "created_at", "updated_at")


class EventDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = EventDelivery
        fields = "__all__"
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class ReactiveTriggerLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReactiveTriggerLog
        fields = "__all__"
        read_only_fields = ("id", "public_id", "created_at", "updated_at")
