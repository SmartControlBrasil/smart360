import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Calendar(models.Model):
    class CalendarType(models.TextChoices):
        OPERATIONAL = "operational", "Operational"
        TECHNICIANS = "technicians", "Technicians"
        PRODUCTION = "production", "Production"
        DELIVERIES = "deliveries", "Deliveries"
        COMMERCIAL = "commercial", "Commercial"
        PERSONAL = "personal", "Personal"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    calendar_type = models.CharField(max_length=20, choices=CalendarType.choices, default=CalendarType.OPERATIONAL)
    description = models.TextField(blank=True)
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="owned_calendars",
        null=True,
        blank=True,
    )
    owner_company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="owned_calendars",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scheduling_calendars"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class CalendarEvent(models.Model):
    class EventType(models.TextChoices):
        VISIT = "visit", "Visit"
        PREVENTIVE = "preventive", "Preventive"
        PRODUCTION = "production", "Production"
        REVIEW = "review", "Review"
        DELIVERY = "delivery", "Delivery"
        MEETING = "meeting", "Meeting"
        TASK = "task", "Task"

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        CONFIRMED = "confirmed", "Confirmed"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        MISSED = "missed", "Missed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    calendar = models.ForeignKey(
        "scheduling_center.Calendar",
        on_delete=models.CASCADE,
        related_name="events",
    )
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=EventType.choices, default=EventType.MEETING)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)
    start_at = models.DateTimeField(db_index=True)
    end_at = models.DateTimeField(db_index=True)
    is_all_day = models.BooleanField(default=False)
    location = models.CharField(max_length=255, blank=True)
    timezone = models.CharField(max_length=64, blank=True, default="America/Sao_Paulo")
    related_module = models.CharField(max_length=80, blank=True, db_index=True)
    related_item_type = models.CharField(max_length=80, blank=True)
    related_item_id = models.CharField(max_length=120, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_calendar_events",
        null=True,
        blank=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_calendar_events",
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scheduling_calendar_events"
        ordering = ["start_at", "title"]
        indexes = [
            models.Index(fields=["calendar", "start_at"], name="sched_event_calendar_start_idx"),
            models.Index(fields=["related_module", "status"], name="sched_event_module_status_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.status == self.Status.COMPLETED and not self.metadata.get("completed_at"):
            self.metadata["completed_at"] = timezone.now().isoformat()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class EventParticipant(models.Model):
    class ParticipantType(models.TextChoices):
        INTERNAL = "internal", "Internal"
        CUSTOMER = "customer", "Customer"
        TECHNICIAN = "technician", "Technician"
        PROVIDER = "provider", "Provider"
        GUEST = "guest", "Guest"

    class ResponseStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        TENTATIVE = "tentative", "Tentative"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    calendar_event = models.ForeignKey(
        "scheduling_center.CalendarEvent",
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="event_participations",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="event_participations",
        null=True,
        blank=True,
    )
    participant_type = models.CharField(max_length=20, choices=ParticipantType.choices, default=ParticipantType.INTERNAL)
    response_status = models.CharField(max_length=20, choices=ResponseStatus.choices, default=ResponseStatus.PENDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scheduling_event_participants"
        ordering = ["calendar_event__start_at", "created_at"]

    def __str__(self) -> str:
        return f"{self.calendar_event} participant"


class RecurrenceRule(models.Model):
    class FrequencyType(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"
        YEARLY = "yearly", "Yearly"
        CUSTOM = "custom", "Custom"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    frequency_type = models.CharField(max_length=20, choices=FrequencyType.choices, default=FrequencyType.WEEKLY)
    interval_value = models.PositiveIntegerField(default=1)
    by_weekday = models.JSONField(default=list, blank=True)
    by_monthday = models.JSONField(default=list, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    occurrences_limit = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    config_json = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scheduling_recurrence_rules"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class RecurringEventLink(models.Model):
    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    parent_event = models.OneToOneField(
        "scheduling_center.CalendarEvent",
        on_delete=models.CASCADE,
        related_name="recurring_link",
    )
    recurrence_rule = models.ForeignKey(
        "scheduling_center.RecurrenceRule",
        on_delete=models.CASCADE,
        related_name="event_links",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scheduling_recurring_event_links"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.parent_event} recurrence"


class EventOccurrence(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        GENERATED = "generated", "Generated"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        MISSED = "missed", "Missed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    recurring_link = models.ForeignKey(
        "scheduling_center.RecurringEventLink",
        on_delete=models.CASCADE,
        related_name="occurrences",
    )
    calendar_event = models.ForeignKey(
        "scheduling_center.CalendarEvent",
        on_delete=models.SET_NULL,
        related_name="generated_occurrences",
        null=True,
        blank=True,
    )
    occurrence_date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    generated_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scheduling_event_occurrences"
        ordering = ["occurrence_date", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["recurring_link", "occurrence_date"],
                name="uniq_sched_occurrence_link_date",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.recurring_link} @ {self.occurrence_date}"


class AvailabilitySlot(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    class SlotType(models.TextChoices):
        TECHNICIAN = "technician", "Technician"
        PRODUCTION = "production", "Production"
        COMMERCIAL = "commercial", "Commercial"
        DELIVERY = "delivery", "Delivery"
        GENERAL = "general", "General"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="availability_slots",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        related_name="availability_slots",
        null=True,
        blank=True,
    )
    calendar = models.ForeignKey(
        "scheduling_center.Calendar",
        on_delete=models.SET_NULL,
        related_name="availability_slots",
        null=True,
        blank=True,
    )
    weekday = models.IntegerField(choices=Weekday.choices, null=True, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_type = models.CharField(max_length=20, choices=SlotType.choices, default=SlotType.GENERAL)
    is_available = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scheduling_availability_slots"
        ordering = ["weekday", "start_time"]

    def __str__(self) -> str:
        return f"{self.slot_type} slot"


class ScheduledReminder(models.Model):
    class ReminderType(models.TextChoices):
        UPCOMING_EVENT = "upcoming_event", "Upcoming Event"
        DEADLINE = "deadline", "Deadline"
        FOLLOW_UP = "follow_up", "Follow Up"
        TASK = "task", "Task"

    class Channel(models.TextChoices):
        IN_APP = "in_app", "In App"
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        WHATSAPP = "whatsapp", "WhatsApp"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    calendar_event = models.ForeignKey(
        "scheduling_center.CalendarEvent",
        on_delete=models.CASCADE,
        related_name="reminders",
    )
    reminder_type = models.CharField(max_length=20, choices=ReminderType.choices, default=ReminderType.UPCOMING_EVENT)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.IN_APP)
    remind_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scheduling_scheduled_reminders"
        ordering = ["remind_at", "created_at"]

    def save(self, *args, **kwargs):
        if self.status == self.Status.SENT and self.sent_at is None:
            self.sent_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.calendar_event} reminder"


class SchedulingTask(models.Model):
    class TaskType(models.TextChoices):
        OPERATIONAL = "operational", "Operational"
        FOLLOW_UP = "follow_up", "Follow Up"
        PRODUCTION = "production", "Production"
        VISIT = "visit", "Visit"
        REVIEW = "review", "Review"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"
        OVERDUE = "overdue", "Overdue"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    task_type = models.CharField(max_length=20, choices=TaskType.choices, default=TaskType.OPERATIONAL)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    due_at = models.DateTimeField(db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="scheduling_tasks",
        null=True,
        blank=True,
    )
    related_module = models.CharField(max_length=80, blank=True, db_index=True)
    related_item_type = models.CharField(max_length=80, blank=True)
    related_item_id = models.CharField(max_length=120, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_scheduling_tasks",
        null=True,
        blank=True,
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scheduling_tasks"
        ordering = ["due_at", "-created_at"]
        indexes = [
            models.Index(fields=["assigned_to", "status"], name="sched_task_assignee_status_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.status == self.Status.COMPLETED and self.completed_at is None:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title

