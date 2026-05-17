import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0002_sitemembership"),
        ("smart_system", "0009_maintenance_contracts"),
        ("analytics_platform", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OperationalMetrics",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "period_type",
                    models.CharField(
                        choices=[
                            ("daily", "Daily"),
                            ("monthly", "Monthly"),
                            ("quarterly", "Quarterly"),
                            ("yearly", "Yearly"),
                        ],
                        default="monthly",
                        max_length=20,
                    ),
                ),
                ("period_start", models.DateField(db_index=True)),
                ("period_end", models.DateField(db_index=True)),
                ("total_work_orders", models.PositiveIntegerField(default=0)),
                ("total_preventives", models.PositiveIntegerField(default=0)),
                ("total_correctives", models.PositiveIntegerField(default=0)),
                ("total_revenue", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("total_cost", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("total_profit", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("avg_response_time", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("avg_execution_time", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("sla_compliance_rate", models.DecimalField(decimal_places=2, default=0, max_digits=7)),
                ("total_sla_compliant", models.PositiveIntegerField(default=0)),
                ("total_sla_violated", models.PositiveIntegerField(default=0)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("calculated_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="operational_metrics",
                        to="companies.company",
                    ),
                ),
            ],
            options={
                "db_table": "analytics_operational_metrics",
                "ordering": ["-period_start", "company__name"],
            },
        ),
        migrations.CreateModel(
            name="ClientProfitability",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "period_type",
                    models.CharField(
                        choices=[
                            ("monthly", "Monthly"),
                            ("quarterly", "Quarterly"),
                            ("yearly", "Yearly"),
                        ],
                        default="monthly",
                        max_length=20,
                    ),
                ),
                ("period_start", models.DateField(db_index=True)),
                ("period_end", models.DateField(db_index=True)),
                ("revenue", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("cost", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("profit", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("margin", models.DecimalField(decimal_places=2, default=0, max_digits=7)),
                ("total_work_orders", models.PositiveIntegerField(default=0)),
                ("total_assets", models.PositiveIntegerField(default=0)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("calculated_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profitability_snapshots",
                        to="smart_system.maintenanceclient",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="client_profitability_snapshots",
                        to="companies.company",
                    ),
                ),
            ],
            options={
                "db_table": "analytics_client_profitability",
                "ordering": ["-period_start", "client__display_name"],
            },
        ),
        migrations.CreateModel(
            name="ContractProfitability",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "period_type",
                    models.CharField(
                        choices=[
                            ("monthly", "Monthly"),
                            ("quarterly", "Quarterly"),
                            ("yearly", "Yearly"),
                        ],
                        default="monthly",
                        max_length=20,
                    ),
                ),
                ("period_start", models.DateField(db_index=True)),
                ("period_end", models.DateField(db_index=True)),
                ("revenue", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("cost", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("profit", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("margin", models.DecimalField(decimal_places=2, default=0, max_digits=7)),
                ("total_work_orders", models.PositiveIntegerField(default=0)),
                ("total_assets", models.PositiveIntegerField(default=0)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("calculated_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contract_profitability_snapshots",
                        to="companies.company",
                    ),
                ),
                (
                    "contract",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profitability_snapshots",
                        to="smart_system.maintenancecontract",
                    ),
                ),
            ],
            options={
                "db_table": "analytics_contract_profitability",
                "ordering": ["-period_start", "contract__contract_number"],
            },
        ),
        migrations.CreateModel(
            name="TechnicianPerformance",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "period_type",
                    models.CharField(
                        choices=[
                            ("monthly", "Monthly"),
                            ("quarterly", "Quarterly"),
                            ("yearly", "Yearly"),
                        ],
                        default="monthly",
                        max_length=20,
                    ),
                ),
                ("period_start", models.DateField(db_index=True)),
                ("period_end", models.DateField(db_index=True)),
                ("jobs_completed", models.PositiveIntegerField(default=0)),
                ("jobs_in_progress", models.PositiveIntegerField(default=0)),
                ("avg_execution_time", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("customer_rating", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("profit_generated", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("total_labor_minutes", models.PositiveIntegerField(default=0)),
                ("total_response_minutes", models.PositiveIntegerField(default=0)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("calculated_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="technician_performance_snapshots",
                        to="companies.company",
                    ),
                ),
                (
                    "technician",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="technician_performance_snapshots",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "analytics_technician_performance",
                "ordering": ["-period_start", "technician__email"],
            },
        ),
        migrations.AddConstraint(
            model_name="operationalmetrics",
            constraint=models.UniqueConstraint(
                fields=("company", "period_type", "period_start"),
                name="uniq_analytics_operational_metrics_period",
            ),
        ),
        migrations.AddConstraint(
            model_name="clientprofitability",
            constraint=models.UniqueConstraint(
                fields=("client", "period_type", "period_start"),
                name="uniq_analytics_client_profitability_period",
            ),
        ),
        migrations.AddConstraint(
            model_name="contractprofitability",
            constraint=models.UniqueConstraint(
                fields=("contract", "period_type", "period_start"),
                name="uniq_analytics_contract_profitability_period",
            ),
        ),
        migrations.AddConstraint(
            model_name="technicianperformance",
            constraint=models.UniqueConstraint(
                fields=("company", "technician", "period_type", "period_start"),
                name="uniq_analytics_technician_performance_period",
            ),
        ),
    ]
