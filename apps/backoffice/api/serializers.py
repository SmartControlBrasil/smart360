from rest_framework import serializers

from ..models import (
    BackofficeAlert,
    BackofficeNote,
    BackofficeQueue,
    BackofficeQueueItem,
    BackofficeQuickAction,
    BackofficeTask,
    BackofficeWidget,
)


class BackofficeQueueSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackofficeQueue
        fields = ("id", "public_id", "name", "slug", "queue_type", "source_module", "description", "is_active", "ordering", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class BackofficeQueueItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackofficeQueueItem
        fields = (
            "id",
            "public_id",
            "queue",
            "item_type",
            "item_id",
            "reference_label",
            "status",
            "priority",
            "assigned_to",
            "due_at",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class BackofficeAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackofficeAlert
        fields = (
            "id",
            "public_id",
            "title",
            "slug",
            "alert_type",
            "source_module",
            "severity",
            "status",
            "related_item_type",
            "related_item_id",
            "summary",
            "details",
            "created_at",
            "resolved_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "slug", "created_at", "resolved_at", "updated_at")


class BackofficeTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackofficeTask
        fields = (
            "id",
            "public_id",
            "title",
            "task_type",
            "source_module",
            "assigned_to",
            "status",
            "priority",
            "due_at",
            "related_item_type",
            "related_item_id",
            "notes",
            "created_at",
            "completed_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "created_at", "completed_at", "updated_at")


class BackofficeQuickActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackofficeQuickAction
        fields = (
            "id",
            "public_id",
            "name",
            "slug",
            "target_module",
            "action_type",
            "label",
            "route_path",
            "config_json",
            "is_active",
            "ordering",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class BackofficeWidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackofficeWidget
        fields = (
            "id",
            "public_id",
            "name",
            "slug",
            "widget_type",
            "source_module",
            "title",
            "config_json",
            "is_active",
            "ordering",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class BackofficeNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackofficeNote
        fields = ("id", "public_id", "note_type", "related_item_type", "related_item_id", "created_by", "content", "is_private", "created_at", "updated_at")
        read_only_fields = ("id", "public_id", "created_at", "updated_at")

