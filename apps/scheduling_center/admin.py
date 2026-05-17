from django.contrib import admin

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


class EventParticipantInline(admin.TabularInline):
    model = EventParticipant
    extra = 0


class ScheduledReminderInline(admin.TabularInline):
    model = ScheduledReminder
    extra = 0


@admin.register(Calendar)
class CalendarAdmin(admin.ModelAdmin):
    list_display = ("name", "calendar_type", "owner_user", "owner_company", "is_active", "updated_at")
    list_filter = ("calendar_type", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "calendar",
        "event_type",
        "status",
        "start_at",
        "end_at",
        "assigned_to",
        "related_module",
    )
    list_filter = ("calendar", "event_type", "status", "is_all_day", "related_module")
    search_fields = ("title", "description", "location", "related_item_type", "related_item_id")
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = [EventParticipantInline, ScheduledReminderInline]


@admin.register(EventParticipant)
class EventParticipantAdmin(admin.ModelAdmin):
    list_display = ("calendar_event", "user", "company", "participant_type", "response_status", "created_at")
    list_filter = ("participant_type", "response_status")
    search_fields = ("calendar_event__title", "user__email", "company__name", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(RecurrenceRule)
class RecurrenceRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "frequency_type", "interval_value", "start_date", "end_date", "is_active")
    list_filter = ("frequency_type", "is_active")
    search_fields = ("name", "slug")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(RecurringEventLink)
class RecurringEventLinkAdmin(admin.ModelAdmin):
    list_display = ("parent_event", "recurrence_rule", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("parent_event__title", "recurrence_rule__name")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(EventOccurrence)
class EventOccurrenceAdmin(admin.ModelAdmin):
    list_display = ("recurring_link", "occurrence_date", "status", "calendar_event", "generated_at")
    list_filter = ("status", "occurrence_date")
    search_fields = ("recurring_link__parent_event__title", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ("slot_type", "user", "company", "calendar", "weekday", "start_time", "end_time", "is_available")
    list_filter = ("slot_type", "weekday", "is_available")
    search_fields = ("user__email", "company__name", "calendar__name", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(ScheduledReminder)
class ScheduledReminderAdmin(admin.ModelAdmin):
    list_display = ("calendar_event", "reminder_type", "channel", "remind_at", "status", "sent_at")
    list_filter = ("reminder_type", "channel", "status")
    search_fields = ("calendar_event__title",)
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(SchedulingTask)
class SchedulingTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "task_type", "priority", "status", "due_at", "assigned_to", "related_module")
    list_filter = ("task_type", "priority", "status", "related_module")
    search_fields = ("title", "description", "related_item_type", "related_item_id")
    readonly_fields = ("public_id", "created_at", "updated_at")

