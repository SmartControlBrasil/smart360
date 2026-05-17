from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0002_sitemembership"),
        ("smart_system", "0008_service_quotes"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaintenanceContract",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("contract_number", models.CharField(max_length=40, unique=True)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("active", "Active"),
                            ("suspended", "Suspended"),
                            ("expired", "Expired"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                (
                    "billing_frequency",
                    models.CharField(
                        choices=[
                            ("monthly", "Monthly"),
                            ("bimonthly", "Bimonthly"),
                            ("quarterly", "Quarterly"),
                            ("semiannual", "Semiannual"),
                            ("yearly", "Yearly"),
                            ("custom_days", "Custom Days"),
                        ],
                        default="monthly",
                        max_length=20,
                    ),
                ),
                ("billing_frequency_days", models.PositiveIntegerField(default=30)),
                ("contract_value", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("next_billing_date", models.DateField(blank=True, null=True)),
                ("last_billing_date", models.DateField(blank=True, null=True)),
                ("auto_generate_preventives", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="maintenance_contracts",
                        to="smart_system.maintenanceclient",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="maintenance_contracts",
                        to="companies.company",
                    ),
                ),
                (
                    "operational_site",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="maintenance_contracts",
                        to="smart_system.operationalsite",
                    ),
                ),
            ],
            options={
                "db_table": "smart_system_maintenance_contracts",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ContractAsset",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                (
                    "maintenance_frequency",
                    models.CharField(
                        choices=[
                            ("monthly", "Monthly"),
                            ("bimonthly", "Bimonthly"),
                            ("quarterly", "Quarterly"),
                            ("semiannual", "Semiannual"),
                            ("yearly", "Yearly"),
                            ("custom_days", "Custom Days"),
                        ],
                        default="monthly",
                        max_length=20,
                    ),
                ),
                ("maintenance_frequency_days", models.PositiveIntegerField(default=30)),
                ("estimated_duration_minutes", models.PositiveIntegerField(default=120)),
                ("last_execution", models.DateField(blank=True, null=True)),
                ("next_execution", models.DateField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("notes", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "asset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="contract_links",
                        to="smart_system.asset",
                    ),
                ),
                (
                    "contract",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="covered_assets",
                        to="smart_system.maintenancecontract",
                    ),
                ),
            ],
            options={
                "db_table": "smart_system_contract_assets",
                "ordering": ["contract__contract_number", "asset__asset_tag"],
            },
        ),
        migrations.AddField(
            model_name="maintenanceplan",
            name="contract_asset",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="maintenance_plans",
                to="smart_system.contractasset",
            ),
        ),
        migrations.AddField(
            model_name="maintenanceplan",
            name="maintenance_contract",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="maintenance_plans",
                to="smart_system.maintenancecontract",
            ),
        ),
        migrations.AddField(
            model_name="serviceorder",
            name="contract_asset",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="service_orders",
                to="smart_system.contractasset",
            ),
        ),
        migrations.AddField(
            model_name="serviceorder",
            name="maintenance_contract",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="service_orders",
                to="smart_system.maintenancecontract",
            ),
        ),
        migrations.AddConstraint(
            model_name="contractasset",
            constraint=models.UniqueConstraint(
                fields=("contract", "asset"),
                name="uniq_smart_system_contract_asset",
            ),
        ),
    ]
