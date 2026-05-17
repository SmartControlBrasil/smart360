import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AnalyticsDashboard",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("description", models.TextField(blank=True)),
                ("layout_config", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "analytics_dashboards", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="AnalyticsDimension",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("slug", models.SlugField(blank=True, max_length=140, unique=True)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "analytics_dimensions", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="AnalyticsMetric",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("metric_name", models.CharField(max_length=160)),
                ("metric_slug", models.SlugField(blank=True, max_length=180, unique=True)),
                (
                    "metric_type",
                    models.CharField(
                        choices=[
                            ("counter", "Counter"),
                            ("gauge", "Gauge"),
                            ("percentage", "Percentage"),
                            ("currency", "Currency"),
                            ("duration", "Duration"),
                            ("ratio", "Ratio"),
                        ],
                        default="counter",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("unit", models.CharField(blank=True, max_length=40)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "analytics_metrics", "ordering": ["metric_name"]},
        ),
        migrations.CreateModel(
            name="AnalyticsReport",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=180, unique=True)),
                ("description", models.TextField(blank=True)),
                (
                    "report_type",
                    models.CharField(
                        choices=[
                            ("operational", "Operational"),
                            ("executive", "Executive"),
                            ("financial", "Financial"),
                            ("technical", "Technical"),
                            ("custom", "Custom"),
                        ],
                        default="operational",
                        max_length=20,
                    ),
                ),
                ("config_json", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "analytics_reports", "ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="AnalyticsSnapshot",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("snapshot_type", models.CharField(db_index=True, max_length=120)),
                ("snapshot_date", models.DateField(db_index=True)),
                ("data_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "analytics_snapshots", "ordering": ["-snapshot_date", "-created_at"]},
        ),
        migrations.CreateModel(
            name="AnalyticsEvent",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("event_type", models.CharField(db_index=True, max_length=120)),
                ("source_module", models.CharField(db_index=True, max_length=80)),
                ("entity_type", models.CharField(blank=True, max_length=80)),
                ("entity_id", models.CharField(blank=True, max_length=120)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("occurred_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="analytics_events",
                        to="companies.company",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="analytics_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"db_table": "analytics_events", "ordering": ["-occurred_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="AnalyticsMetricValue",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("dimension_value", models.CharField(blank=True, max_length=160)),
                ("value", models.DecimalField(decimal_places=4, max_digits=18)),
                ("calculated_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("reference_date", models.DateField(blank=True, db_index=True, null=True)),
                ("source_module", models.CharField(blank=True, max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dimension",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="metric_values",
                        to="analytics_platform.analyticsdimension",
                    ),
                ),
                (
                    "metric",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="values",
                        to="analytics_platform.analyticsmetric",
                    ),
                ),
            ],
            options={"db_table": "analytics_metric_values", "ordering": ["-calculated_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="AnalyticsWidget",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "widget_type",
                    models.CharField(
                        choices=[
                            ("metric_card", "Metric Card"),
                            ("line_chart", "Line Chart"),
                            ("bar_chart", "Bar Chart"),
                            ("pie_chart", "Pie Chart"),
                            ("table", "Table"),
                        ],
                        default="metric_card",
                        max_length=30,
                    ),
                ),
                ("title", models.CharField(max_length=160)),
                ("config_json", models.JSONField(blank=True, default=dict)),
                ("ordering", models.PositiveIntegerField(default=1)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dashboard",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="widgets",
                        to="analytics_platform.analyticsdashboard",
                    ),
                ),
                (
                    "metric",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="widgets",
                        to="analytics_platform.analyticsmetric",
                    ),
                ),
            ],
            options={"db_table": "analytics_widgets", "ordering": ["dashboard__name", "ordering", "title"]},
        ),
        migrations.AddIndex(
            model_name="analyticsmetricvalue",
            index=models.Index(fields=["source_module", "reference_date"], name="analytics_mv_src_ref_idx"),
        ),
        migrations.AddConstraint(
            model_name="analyticswidget",
            constraint=models.UniqueConstraint(fields=("dashboard", "ordering"), name="uniq_analytics_widget_dashboard_ordering"),
        ),
    ]

