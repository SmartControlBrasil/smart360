from django.db import migrations, models
import django.db.models.deletion


def backfill_scope(apps, schema_editor):
    Checklist = apps.get_model("smart_system", "Checklist")
    MaintenancePlan = apps.get_model("smart_system", "MaintenancePlan")

    for checklist in Checklist.objects.select_related("operational_site__maintenance_client__company").all():
        if checklist.operational_site_id and checklist.company_id is None:
            checklist.company_id = checklist.operational_site.maintenance_client.company_id
            checklist.save(update_fields=["company"])

    for plan in MaintenancePlan.objects.select_related("asset__operational_site__maintenance_client__company").all():
        updated_fields = []
        if plan.asset_id:
            if plan.operational_site_id is None:
                plan.operational_site_id = plan.asset.operational_site_id
                updated_fields.append("operational_site")
            if plan.company_id is None:
                plan.company_id = plan.asset.operational_site.maintenance_client.company_id
                updated_fields.append("company")
        elif plan.operational_site_id and plan.company_id is None:
            plan.company_id = plan.operational_site.maintenance_client.company_id
            updated_fields.append("company")

        if updated_fields:
            plan.save(update_fields=updated_fields)


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0002_sitemembership"),
        ("smart_system", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="checklist",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="smart_system_checklists",
                to="companies.company",
            ),
        ),
        migrations.AddField(
            model_name="checklist",
            name="operational_site",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="checklists",
                to="smart_system.operationalsite",
            ),
        ),
        migrations.AddField(
            model_name="maintenanceplan",
            name="company",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="smart_system_maintenance_plans",
                to="companies.company",
            ),
        ),
        migrations.AddField(
            model_name="maintenanceplan",
            name="operational_site",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="maintenance_plans",
                to="smart_system.operationalsite",
            ),
        ),
        migrations.RunPython(backfill_scope, migrations.RunPython.noop),
    ]
