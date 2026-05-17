from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0002_sitemembership"),
        ("marketplace_technicians", "0003_matching_score_breakdown"),
        ("smart_system", "0006_field_offline_sync"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TechnicianAvailabilityWindow",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("weekday", models.PositiveSmallIntegerField(blank=True, choices=[(1, "Monday"), (2, "Tuesday"), (3, "Wednesday"), (4, "Thursday"), (5, "Friday"), (6, "Saturday"), (7, "Sunday")], null=True)),
                ("blocked_date", models.DateField(blank=True, null=True)),
                ("start_time", models.TimeField(blank=True, null=True)),
                ("end_time", models.TimeField(blank=True, null=True)),
                ("is_available", models.BooleanField(default=True)),
                ("max_daily_jobs", models.PositiveIntegerField(default=6)),
                ("max_daily_hours", models.PositiveIntegerField(default=8)),
                ("notes", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="technician_availability_windows", to="companies.company")),
                ("operational_site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="technician_availability_windows", to="smart_system.operationalsite")),
                ("technician", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="technician_availability_windows", to=settings.AUTH_USER_MODEL)),
                ("technician_profile", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="availability_windows", to="marketplace_technicians.technicianprofile")),
            ],
            options={
                "db_table": "smart_system_technician_availability_windows",
                "ordering": ["technician_id", "weekday", "blocked_date", "start_time"],
            },
        ),
        migrations.CreateModel(
            name="TechnicianSchedule",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("date", models.DateField(db_index=True)),
                ("total_jobs", models.PositiveIntegerField(default=0)),
                ("total_estimated_duration", models.PositiveIntegerField(default=0)),
                ("total_estimated_travel", models.PositiveIntegerField(default=0)),
                ("total_conflicts", models.PositiveIntegerField(default=0)),
                ("notes", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="technician_schedules", to="companies.company")),
                ("operational_site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="technician_schedules", to="smart_system.operationalsite")),
                ("technician", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="smart_system_schedules", to=settings.AUTH_USER_MODEL)),
                ("technician_profile", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="smart_system_schedules", to="marketplace_technicians.technicianprofile")),
            ],
            options={
                "db_table": "smart_system_technician_schedules",
                "ordering": ["date", "technician_id"],
            },
        ),
        migrations.CreateModel(
            name="RoutePlan",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("date", models.DateField(db_index=True)),
                ("total_stops", models.PositiveIntegerField(default=0)),
                ("total_estimated_duration", models.PositiveIntegerField(default=0)),
                ("total_estimated_travel", models.PositiveIntegerField(default=0)),
                ("optimization_status", models.CharField(choices=[("draft", "Draft"), ("generated", "Generated"), ("manual", "Manual"), ("needs_review", "Needs Review")], default="draft", max_length=20)),
                ("route_summary", models.JSONField(blank=True, default=dict)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="route_plans", to="companies.company")),
                ("operational_site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="route_plans", to="smart_system.operationalsite")),
                ("technician", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="route_plans", to=settings.AUTH_USER_MODEL)),
                ("technician_profile", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="route_plans", to="marketplace_technicians.technicianprofile")),
            ],
            options={
                "db_table": "smart_system_route_plans",
                "ordering": ["-date", "technician_id"],
            },
        ),
        migrations.CreateModel(
            name="ScheduledVisit",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("source_type", models.CharField(choices=[("work_order", "Work Order"), ("preventive", "Preventive"), ("marketplace", "Marketplace Assignment"), ("manual", "Manual")], default="work_order", max_length=20)),
                ("title", models.CharField(max_length=180)),
                ("scheduled_date", models.DateField(db_index=True)),
                ("scheduled_start", models.DateTimeField(blank=True, null=True)),
                ("scheduled_end", models.DateTimeField(blank=True, null=True)),
                ("window_start", models.TimeField(blank=True, null=True)),
                ("window_end", models.TimeField(blank=True, null=True)),
                ("estimated_duration_minutes", models.PositiveIntegerField(default=60)),
                ("estimated_travel_minutes", models.PositiveIntegerField(default=0)),
                ("priority", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("urgent", "Urgent")], default="medium", max_length=20)),
                ("status", models.CharField(choices=[("pending_assignment", "Pending Assignment"), ("scheduled", "Scheduled"), ("confirmed", "Confirmed"), ("in_progress", "In Progress"), ("completed", "Completed"), ("cancelled", "Cancelled")], default="pending_assignment", max_length=24)),
                ("route_order", models.PositiveIntegerField(default=0)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("location_label", models.CharField(blank=True, max_length=180)),
                ("conflict_flags", models.JSONField(blank=True, default=list)),
                ("notes", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("asset", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="scheduled_visits", to="smart_system.asset")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="scheduled_visits", to="companies.company")),
                ("maintenance_plan", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="scheduled_visits", to="smart_system.maintenanceplan")),
                ("operational_site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="scheduled_visits", to="smart_system.operationalsite")),
                ("route_plan", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="visits", to="smart_system.routeplan")),
                ("service_assignment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="scheduled_visits", to="marketplace_technicians.technicianassignment")),
                ("technician", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="scheduled_visits", to=settings.AUTH_USER_MODEL)),
                ("technician_profile", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="scheduled_visits", to="marketplace_technicians.technicianprofile")),
                ("technician_schedule", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="visits", to="smart_system.technicianschedule")),
                ("work_order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="scheduled_visits", to="smart_system.serviceorder")),
            ],
            options={
                "db_table": "smart_system_scheduled_visits",
                "ordering": ["scheduled_date", "route_order", "scheduled_start", "title"],
            },
        ),
        migrations.AddConstraint(
            model_name="technicianschedule",
            constraint=models.UniqueConstraint(fields=("company", "technician", "date"), name="uniq_smart_system_schedule_company_technician_date"),
        ),
        migrations.AddConstraint(
            model_name="routeplan",
            constraint=models.UniqueConstraint(fields=("company", "technician", "date"), name="uniq_smart_system_route_plan_company_technician_date"),
        ),
        migrations.AddIndex(
            model_name="technicianavailabilitywindow",
            index=models.Index(fields=["company", "technician"], name="smart_availability_company_tech_idx"),
        ),
        migrations.AddIndex(
            model_name="technicianavailabilitywindow",
            index=models.Index(fields=["blocked_date", "is_available"], name="smart_availability_blocked_idx"),
        ),
        migrations.AddIndex(
            model_name="scheduledvisit",
            index=models.Index(fields=["company", "scheduled_date"], name="smart_visit_company_date_idx"),
        ),
        migrations.AddIndex(
            model_name="scheduledvisit",
            index=models.Index(fields=["technician", "scheduled_date"], name="smart_visit_technician_date_idx"),
        ),
        migrations.AddIndex(
            model_name="scheduledvisit",
            index=models.Index(fields=["status", "scheduled_date"], name="smart_visit_status_date_idx"),
        ),
    ]
