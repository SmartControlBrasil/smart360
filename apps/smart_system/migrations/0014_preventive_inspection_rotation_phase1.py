# Generated manually for Phase 1 — Plano rotativo de inspecao

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("companies", "0002_sitemembership"),
        ("smart_system", "0013_alter_maintenanceplan_updated_at_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PreventiveInspectionRoutine",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "checklist",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="preventive_inspection_routines",
                        to="smart_system.checklist",
                    ),
                ),
                (
                    "company",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="preventive_inspection_routines",
                        to="companies.company",
                    ),
                ),
                (
                    "operational_site",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="preventive_inspection_routines",
                        to="smart_system.operationalsite",
                    ),
                ),
            ],
            options={
                "db_table": "smart_system_preventive_inspection_routines",
                "ordering": ["operational_site__name", "name"],
            },
        ),
        migrations.CreateModel(
            name="InspectionDivision",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("name", models.CharField(max_length=180)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "routine",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="divisions",
                        to="smart_system.preventiveinspectionroutine",
                    ),
                ),
            ],
            options={
                "db_table": "smart_system_inspection_divisions",
                "ordering": ["routine_id", "sort_order", "id"],
            },
        ),
        migrations.AddField(
            model_name="preventiveinspectionroutine",
            name="next_division",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="smart_system.inspectiondivision",
            ),
        ),
        migrations.CreateModel(
            name="InspectionDivisionEquipment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("always_include_in_visit", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "asset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inspection_division_links",
                        to="smart_system.asset",
                    ),
                ),
                (
                    "division",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="division_equipment_links",
                        to="smart_system.inspectiondivision",
                    ),
                ),
            ],
            options={
                "db_table": "smart_system_inspection_division_equipment",
                "ordering": ["division_id", "asset__asset_tag"],
            },
        ),
        migrations.AddConstraint(
            model_name="inspectiondivisionequipment",
            constraint=models.UniqueConstraint(fields=("division", "asset"), name="uniq_inspection_division_asset"),
        ),
    ]
