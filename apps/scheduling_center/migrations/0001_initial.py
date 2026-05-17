import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("companies", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Calendar",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                (
                    "calendar_type",
                    models.CharField(
                        choices=[
                            ("operational", "Operational"),
                            ("technicians", "Technicians"),
                            ("production", "Production"),
                            ("deliveries", "Deliveries"),
                            ("commercial", "Commercial"),
                            ("personal", "Personal"),
                        ],
                        default="operational",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner_company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="owned_calendars",
                        to="companies.company",
                    ),
                ),
                (
                    "owner_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="owned_calendars",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "scheduling_calendars", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="RecurrenceRule",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                (
                    "frequency_type",
                    models.CharField(
                        choices=[
                            ("daily", "Daily"),
                            ("weekly", "Weekly"),
                            ("monthly", "Monthly"),
                            ("yearly", "Yearly"),
                            ("custom", "Custom"),
                        ],
                        default="weekly",
                        max_length=20,
                    ),
                ),
                ("interval_value", models.PositiveIntegerField(default=1)),
                ("by_weekday", models.JSONField(blank=True, default=list)),
                ("by_monthday", models.JSONField(blank=True, default=list)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("occurrences_limit", models.PositiveIntegerField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("config_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "scheduling_recurrence_rules", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="AvailabilitySlot",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "weekday",
                    models.IntegerField(
                        blank=True,
                        choices=[
                            (0, "Monday"),
                            (1, "Tuesday"),
                            (2, "Wednesday"),
                            (3, "Thursday"),
                            (4, "Friday"),
                            (5, "Saturday"),
                            (6, "Sunday"),
                        ],
                        null=True,
                    ),
                ),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                (
                    "slot_type",
                    models.CharField(
                        choices=[
                            ("technician", "Technician"),
                            ("production", "Production"),
                            ("commercial", "Commercial"),
                            ("delivery", "Delivery"),
                            ("general", "General"),
                        ],
                        default="general",
                        max_length=20,
                    ),
                ),
                ("is_available", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "calendar",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="availability_slots",
                        to="scheduling_center.calendar",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="availability_slots",
                        to="companies.company",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="availability_slots",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "scheduling_availability_slots", "ordering": ["weekday", "start_time"]},
        ),
        migrations.CreateModel(
            name="CalendarEvent",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("title", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("visit", "Visit"),
                            ("preventive", "Preventive"),
                            ("production", "Production"),
                            ("review", "Review"),
                            ("delivery", "Delivery"),
                            ("meeting", "Meeting"),
                            ("task", "Task"),
                        ],
                        default="meeting",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("scheduled", "Scheduled"),
                            ("confirmed", "Confirmed"),
                            ("in_progress", "In Progress"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                            ("missed", "Missed"),
                        ],
                        default="scheduled",
                        max_length=20,
                    ),
                ),
                ("start_at", models.DateTimeField(db_index=True)),
                ("end_at", models.DateTimeField(db_index=True)),
                ("is_all_day", models.BooleanField(default=False)),
                ("location", models.CharField(blank=True, max_length=255)),
                ("timezone", models.CharField(blank=True, default="America/Sao_Paulo", max_length=64)),
                ("related_module", models.CharField(blank=True, db_index=True, max_length=80)),
                ("related_item_type", models.CharField(blank=True, max_length=80)),
                ("related_item_id", models.CharField(blank=True, max_length=120)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_to",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assigned_calendar_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "calendar",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="scheduling_center.calendar",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_calendar_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "scheduling_calendar_events", "ordering": ["start_at", "title"]},
        ),
        migrations.CreateModel(
            name="SchedulingTask",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("title", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                (
                    "task_type",
                    models.CharField(
                        choices=[
                            ("operational", "Operational"),
                            ("follow_up", "Follow Up"),
                            ("production", "Production"),
                            ("visit", "Visit"),
                            ("review", "Review"),
                        ],
                        default="operational",
                        max_length=20,
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("low", "Low"),
                            ("medium", "Medium"),
                            ("high", "High"),
                            ("urgent", "Urgent"),
                        ],
                        default="medium",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("in_progress", "In Progress"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                            ("overdue", "Overdue"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("due_at", models.DateTimeField(db_index=True)),
                ("related_module", models.CharField(blank=True, db_index=True, max_length=80)),
                ("related_item_type", models.CharField(blank=True, max_length=80)),
                ("related_item_id", models.CharField(blank=True, max_length=120)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assigned_to",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scheduling_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_scheduling_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "scheduling_tasks", "ordering": ["due_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="ScheduledReminder",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "reminder_type",
                    models.CharField(
                        choices=[
                            ("upcoming_event", "Upcoming Event"),
                            ("deadline", "Deadline"),
                            ("follow_up", "Follow Up"),
                            ("task", "Task"),
                        ],
                        default="upcoming_event",
                        max_length=20,
                    ),
                ),
                (
                    "channel",
                    models.CharField(
                        choices=[
                            ("in_app", "In App"),
                            ("email", "Email"),
                            ("sms", "SMS"),
                            ("whatsapp", "WhatsApp"),
                        ],
                        default="in_app",
                        max_length=20,
                    ),
                ),
                ("remind_at", models.DateTimeField(db_index=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("sent", "Sent"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "calendar_event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reminders",
                        to="scheduling_center.calendarevent",
                    ),
                ),
            ],
            options={"db_table": "scheduling_scheduled_reminders", "ordering": ["remind_at", "created_at"]},
        ),
        migrations.CreateModel(
            name="RecurringEventLink",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "parent_event",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recurring_link",
                        to="scheduling_center.calendarevent",
                    ),
                ),
                (
                    "recurrence_rule",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="event_links",
                        to="scheduling_center.recurrencerule",
                    ),
                ),
            ],
            options={"db_table": "scheduling_recurring_event_links", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="EventParticipant",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "participant_type",
                    models.CharField(
                        choices=[
                            ("internal", "Internal"),
                            ("customer", "Customer"),
                            ("technician", "Technician"),
                            ("provider", "Provider"),
                            ("guest", "Guest"),
                        ],
                        default="internal",
                        max_length=20,
                    ),
                ),
                (
                    "response_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("accepted", "Accepted"),
                            ("declined", "Declined"),
                            ("tentative", "Tentative"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "calendar_event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="participants",
                        to="scheduling_center.calendarevent",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="event_participations",
                        to="companies.company",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="event_participations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "scheduling_event_participants", "ordering": ["calendar_event__start_at", "created_at"]},
        ),
        migrations.CreateModel(
            name="EventOccurrence",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("occurrence_date", models.DateField(db_index=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("generated", "Generated"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                            ("missed", "Missed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("generated_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "calendar_event",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="generated_occurrences",
                        to="scheduling_center.calendarevent",
                    ),
                ),
                (
                    "recurring_link",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="occurrences",
                        to="scheduling_center.recurringeventlink",
                    ),
                ),
            ],
            options={"db_table": "scheduling_event_occurrences", "ordering": ["occurrence_date", "created_at"]},
        ),
        migrations.AddIndex(
            model_name="calendarevent",
            index=models.Index(fields=["calendar", "start_at"], name="sched_event_calendar_start_idx"),
        ),
        migrations.AddIndex(
            model_name="calendarevent",
            index=models.Index(fields=["related_module", "status"], name="sched_event_module_status_idx"),
        ),
        migrations.AddIndex(
            model_name="schedulingtask",
            index=models.Index(fields=["assigned_to", "status"], name="sched_task_assignee_status_idx"),
        ),
        migrations.AddConstraint(
            model_name="eventoccurrence",
            constraint=models.UniqueConstraint(
                fields=("recurring_link", "occurrence_date"),
                name="uniq_sched_occurrence_link_date",
            ),
        ),
    ]

