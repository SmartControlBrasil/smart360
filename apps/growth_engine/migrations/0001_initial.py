import django.db.models.deletion
import django.utils.timezone
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("smart_site_factory", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LeadCampaign",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=150)),
                ("objective", models.CharField(max_length=180)),
                (
                    "channel",
                    models.CharField(
                        choices=[("meta", "Meta Ads"), ("google", "Google Ads"), ("email", "Email"), ("whatsapp", "WhatsApp"), ("organic", "Organic")],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Draft"), ("active", "Active"), ("paused", "Paused"), ("finished", "Finished")],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "growth_lead_campaigns", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="LeadSource",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=120, unique=True)),
                (
                    "source_type",
                    models.CharField(
                        choices=[("organic", "Organic"), ("paid", "Paid"), ("referral", "Referral"), ("social", "Social"), ("partner", "Partner")],
                        default="organic",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "growth_lead_sources", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="LeadTag",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=80, unique=True)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "growth_lead_tags", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="Lead",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("company_name", models.CharField(max_length=180)),
                ("contact_name", models.CharField(blank=True, max_length=150)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("whatsapp", models.CharField(blank=True, max_length=30)),
                ("website", models.URLField(blank=True)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                (
                    "status",
                    models.CharField(
                        choices=[("new", "New"), ("contacted", "Contacted"), ("qualified", "Qualified"), ("proposal", "Proposal"), ("won", "Won"), ("lost", "Lost")],
                        default="new",
                        max_length=20,
                    ),
                ),
                ("score", models.PositiveIntegerField(default=0)),
                ("notes", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_leads", to=settings.AUTH_USER_MODEL)),
                ("campaign", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="leads", to="growth_engine.leadcampaign")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_leads", to=settings.AUTH_USER_MODEL)),
                ("niche", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="growth_leads", to="smart_site_factory.niche")),
                ("source", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="leads", to="growth_engine.leadsource")),
                ("tags", models.ManyToManyField(blank=True, related_name="leads", to="growth_engine.leadtag")),
            ],
            options={"db_table": "growth_leads", "ordering": ["-score", "-created_at"]},
        ),
        migrations.CreateModel(
            name="LeadQualification",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("criteria", models.JSONField(blank=True, default=dict)),
                ("calculated_score", models.PositiveIntegerField(default=0)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("lead", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="qualification", to="growth_engine.lead")),
            ],
            options={"db_table": "growth_lead_qualifications"},
        ),
        migrations.CreateModel(
            name="LeadInteraction",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "interaction_type",
                    models.CharField(
                        choices=[("call", "Call"), ("email", "Email"), ("whatsapp", "WhatsApp"), ("meeting", "Meeting"), ("note", "Note")],
                        max_length=20,
                    ),
                ),
                (
                    "channel",
                    models.CharField(
                        choices=[("phone", "Phone"), ("whatsapp", "WhatsApp"), ("email", "Email"), ("instagram", "Instagram"), ("other", "Other")],
                        max_length=20,
                    ),
                ),
                ("summary", models.TextField()),
                ("happened_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("lead", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="interactions", to="growth_engine.lead")),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="lead_interactions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "growth_lead_interactions", "ordering": ["-happened_at"]},
        ),
        migrations.CreateModel(
            name="LeadAssignment",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("reassigned", "Reassigned"), ("completed", "Completed")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("assigned_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("lead", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="assignments", to="growth_engine.lead")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lead_assignments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "growth_lead_assignments", "ordering": ["-assigned_at"]},
        ),
    ]
