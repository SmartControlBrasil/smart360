import decimal
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
            name="Niche",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=120, unique=True)),
                ("slug", models.SlugField(max_length=140, unique=True)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "ssf_niches", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="ConfiguratorQuestion",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("text", models.CharField(max_length=255)),
                (
                    "question_type",
                    models.CharField(
                        choices=[
                            ("single_choice", "Single Choice"),
                            ("multiple_choice", "Multiple Choice"),
                            ("text", "Text"),
                            ("boolean", "Boolean"),
                        ],
                        default="single_choice",
                        max_length=20,
                    ),
                ),
                ("order", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "niche",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="questions", to="smart_site_factory.niche"),
                ),
            ],
            options={"db_table": "ssf_configurator_questions", "ordering": ["order", "id"]},
        ),
        migrations.CreateModel(
            name="Template",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=150)),
                ("slug", models.SlugField(max_length=180, unique=True)),
                ("description", models.TextField(blank=True)),
                ("version", models.CharField(default="1.0.0", max_length=40)),
                (
                    "template_type",
                    models.CharField(
                        choices=[("one_page", "One Page"), ("multi_page", "Multi Page"), ("landing_page", "Landing Page")],
                        default="one_page",
                        max_length=20,
                    ),
                ),
                ("base_price", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=10)),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Draft"), ("ready", "Ready"), ("deprecated", "Deprecated")],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("niche", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="templates", to="smart_site_factory.niche")),
            ],
            options={"db_table": "ssf_templates", "ordering": ["niche__name", "name"]},
        ),
        migrations.AddConstraint(
            model_name="template",
            constraint=models.UniqueConstraint(fields=("niche", "name", "version"), name="uniq_ssf_template_version"),
        ),
        migrations.CreateModel(
            name="ConfiguratorOption",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("label", models.CharField(max_length=120)),
                ("value", models.CharField(max_length=120)),
                ("order", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="options", to="smart_site_factory.configuratorquestion")),
            ],
            options={"db_table": "ssf_configurator_options", "ordering": ["question__order", "order", "id"]},
        ),
        migrations.AddConstraint(
            model_name="configuratoroption",
            constraint=models.UniqueConstraint(fields=("question", "value"), name="uniq_ssf_option_per_question"),
        ),
        migrations.CreateModel(
            name="SiteOrder",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("intake_pending", "Intake Pending"),
                            ("in_production", "In Production"),
                            ("review", "Review"),
                            ("delivered", "Delivered"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="intake_pending",
                        max_length=30,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("final_price", models.DecimalField(decimal_places=2, default=decimal.Decimal("0.00"), max_digits=10)),
                ("ordered_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("production_started_at", models.DateTimeField(blank=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="site_orders", to="companies.company")),
                ("niche", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="site_orders", to="smart_site_factory.niche")),
                ("recommended_template", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="recommended_orders", to="smart_site_factory.template")),
                ("requester", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="site_orders", to=settings.AUTH_USER_MODEL)),
                ("selected_template", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="selected_orders", to="smart_site_factory.template")),
            ],
            options={"db_table": "ssf_site_orders", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SiteProjectIntake",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("company_name", models.CharField(max_length=180)),
                ("phone", models.CharField(blank=True, max_length=30)),
                ("whatsapp", models.CharField(blank=True, max_length=30)),
                ("address", models.CharField(blank=True, max_length=255)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("state", models.CharField(blank=True, max_length=100)),
                ("business_description", models.TextField(blank=True)),
                ("main_services", models.JSONField(blank=True, default=list)),
                ("instagram", models.URLField(blank=True)),
                ("facebook", models.URLField(blank=True)),
                ("logo_url", models.URLField(blank=True)),
                ("photo_gallery", models.JSONField(blank=True, default=list)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("site_order", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="intake", to="smart_site_factory.siteorder")),
            ],
            options={"db_table": "ssf_site_project_intakes", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SiteOrderAnswer",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("value_text", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("option", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="site_order_answers", to="smart_site_factory.configuratoroption")),
                ("question", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="site_order_answers", to="smart_site_factory.configuratorquestion")),
                ("site_order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="smart_site_factory.siteorder")),
            ],
            options={"db_table": "ssf_site_order_answers", "ordering": ["question__order", "id"]},
        ),
        migrations.CreateModel(
            name="ProductionTask",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "stage",
                    models.CharField(
                        choices=[
                            ("discovery", "Discovery"),
                            ("copywriting", "Copywriting"),
                            ("design", "Design"),
                            ("development", "Development"),
                            ("qa", "QA"),
                            ("delivery", "Delivery"),
                        ],
                        max_length=30,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("todo", "To Do"), ("in_progress", "In Progress"), ("blocked", "Blocked"), ("done", "Done")],
                        default="todo",
                        max_length=20,
                    ),
                ),
                ("due_date", models.DateField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("order", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assignee", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_site_tasks", to=settings.AUTH_USER_MODEL)),
                ("site_order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="production_tasks", to="smart_site_factory.siteorder")),
            ],
            options={"db_table": "ssf_production_tasks", "ordering": ["site_order__created_at", "order", "id"]},
        ),
        migrations.AddConstraint(
            model_name="productiontask",
            constraint=models.UniqueConstraint(fields=("site_order", "stage"), name="uniq_ssf_task_stage_per_order"),
        ),
        migrations.CreateModel(
            name="DeliveryRecord",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("delivered_url", models.URLField()),
                ("delivered_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "acceptance_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("accepted", "Accepted"),
                            ("changes_requested", "Changes Requested"),
                        ],
                        default="pending",
                        max_length=30,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("site_order", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="delivery_record", to="smart_site_factory.siteorder")),
            ],
            options={"db_table": "ssf_delivery_records", "ordering": ["-delivered_at"]},
        ),
        migrations.CreateModel(
            name="TemplateRecommendationRule",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("priority", models.PositiveIntegerField(default=100)),
                ("is_active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("niche", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recommendation_rules", to="smart_site_factory.niche")),
                ("option", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="recommendation_rules", to="smart_site_factory.configuratoroption")),
                ("question", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="recommendation_rules", to="smart_site_factory.configuratorquestion")),
                ("recommended_template", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recommendation_rules", to="smart_site_factory.template")),
            ],
            options={"db_table": "ssf_template_recommendation_rules", "ordering": ["priority", "-created_at"]},
        ),
    ]
