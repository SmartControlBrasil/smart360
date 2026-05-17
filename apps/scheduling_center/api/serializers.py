from rest_framework import serializers

from apps.scheduling_center.models import (
    AvailabilitySlot,
    Calendar,
    CalendarEvent,
    EventOccurrence,
    EventParticipant,
    RecurrenceRule,
    RecurringEventLink,
    ScheduledReminder,
    SchedulingTask,
)


class CalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calendar
        fields = [
            "id",
            "public_id",
            "name",
            "slug",
            "calendar_type",
            "description",
            "owner_user",
            "owner_company",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "slug", "created_at", "updated_at"]


class CalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEvent
        fields = [
            "id",
            "public_id",
            "calendar",
            "title",
            "description",
            "event_type",
            "status",
            "start_at",
            "end_at",
            "is_all_day",
            "location",
            "timezone",
            "related_module",
            "related_item_type",
            "related_item_id",
            "created_by",
            "assigned_to",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]

    def validate(self, attrs):
        start_at = attrs.get("start_at", getattr(self.instance, "start_at", None))
        end_at = attrs.get("end_at", getattr(self.instance, "end_at", None))
        if start_at and end_at and end_at < start_at:
            raise serializers.ValidationError({"end_at": "end_at must be greater than or equal to start_at."})
        return attrs


class EventParticipantSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventParticipant
        fields = [
            "id",
            "public_id",
            "calendar_event",
            "user",
            "company",
            "participant_type",
            "response_status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class RecurrenceRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurrenceRule
        fields = [
            "id",
            "public_id",
            "name",
            "slug",
            "frequency_type",
            "interval_value",
            "by_weekday",
            "by_monthday",
            "start_date",
            "end_date",
            "occurrences_limit",
            "is_active",
            "config_json",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "slug", "created_at", "updated_at"]


class RecurringEventLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecurringEventLink
        fields = [
            "id",
            "public_id",
            "parent_event",
            "recurrence_rule",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class EventOccurrenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventOccurrence
        fields = [
            "id",
            "public_id",
            "recurring_link",
            "calendar_event",
            "occurrence_date",
            "status",
            "generated_at",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]


class AvailabilitySlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailabilitySlot
        fields = [
            "id",
            "public_id",
            "user",
            "company",
            "calendar",
            "weekday",
            "start_time",
            "end_time",
            "slot_type",
            "is_available",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "created_at", "updated_at"]

    def validate(self, attrs):
        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError({"end_time": "end_time must be greater than start_time."})
        return attrs


class ScheduledReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduledReminder
        fields = [
            "id",
            "public_id",
            "calendar_event",
            "reminder_type",
            "channel",
            "remind_at",
            "status",
            "created_at",
            "sent_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "created_at", "updated_at", "sent_at"]


class SchedulingTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchedulingTask
        fields = [
            "id",
            "public_id",
            "title",
            "description",
            "task_type",
            "priority",
            "status",
            "due_at",
            "assigned_to",
            "related_module",
            "related_item_type",
            "related_item_id",
            "created_by",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "public_id", "created_at", "updated_at", "completed_at"]

