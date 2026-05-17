import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0002_sitemembership"),
        ("smart_system", "0011_rename_long_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="maintenanceplan",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="maintenanceplan",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
        ),
        migrations.CreateModel(
            name="EquipmentModel",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("manufacturer", models.CharField(blank=True, max_length=120)),
                ("manufacturer_code", models.CharField(blank=True, max_length=120)),
                ("equipment_type", models.CharField(blank=True, max_length=120)),
                ("is_pmoc_applicable", models.BooleanField(default=False)),
                ("pmoc_frequency", models.CharField(blank=True, max_length=80)),
                ("status", models.CharField(choices=[("active", "Active"), ("inactive", "Inactive"), ("discontinued", "Discontinued")], default="active", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "category",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="equipment_models",
                        to="smart_system.assetcategory",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="smart_system_equipment_models",
                        to="companies.company",
                    ),
                ),
            ],
            options={
                "db_table": "smart_system_equipment_models",
                "ordering": ["company__name", "name"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("company", "name", "manufacturer_code"),
                        name="uniq_smart_system_equipment_model_company_name_code",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="CustomerEquipment",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("display_name", models.CharField(blank=True, max_length=180)),
                ("customer_tag", models.CharField(db_index=True, max_length=60)),
                ("internal_code", models.CharField(blank=True, max_length=80)),
                ("serial_number", models.CharField(blank=True, max_length=120)),
                ("location", models.CharField(blank=True, max_length=180)),
                ("preventive_group", models.CharField(blank=True, choices=[("A", "A"), ("B", "B"), ("C", "C")], max_length=1)),
                ("is_pmoc_applicable", models.BooleanField(blank=True, null=True)),
                ("status", models.CharField(choices=[("active", "Active"), ("inactive", "Inactive"), ("decommissioned", "Decommissioned")], default="active", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("installed_at", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="customer_equipments",
                        to="companies.company",
                    ),
                ),
                (
                    "equipment_model",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="customer_equipments",
                        to="smart_system.equipmentmodel",
                    ),
                ),
                (
                    "site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="customer_equipments",
                        to="smart_system.operationalsite",
                    ),
                ),
            ],
            options={
                "db_table": "smart_system_customer_equipments",
                "ordering": ["company__name", "site__name", "customer_tag"],
                "indexes": [models.Index(fields=["company", "site", "status"], name="sm_ce_scope_idx")],
                "constraints": [
                    models.UniqueConstraint(fields=("company", "customer_tag"), name="uniq_smart_system_customer_equipment_company_tag")
                ],
            },
        ),
        migrations.CreateModel(
            name="EquipmentModelPart",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("quantity_default", models.DecimalField(decimal_places=2, default=1, max_digits=12)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="equipment_model_parts",
                        to="companies.company",
                    ),
                ),
                (
                    "equipment_model",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="parts",
                        to="smart_system.equipmentmodel",
                    ),
                ),
                (
                    "part",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="equipment_models",
                        to="smart_system.part",
                    ),
                ),
            ],
            options={
                "db_table": "smart_system_equipment_model_parts",
                "ordering": ["equipment_model__name", "part__name"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("company", "equipment_model", "part"),
                        name="uniq_smart_system_equipment_model_part",
                    )
                ],
            },
        ),
    ]
