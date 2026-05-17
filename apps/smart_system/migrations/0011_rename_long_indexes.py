from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("smart_system", "0010_alter_serviceorder_status"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="servicesignature",
            old_name="smart_signature_type_current_idx",
            new_name="smart_sig_type_curr_idx",
        ),
        migrations.RenameIndex(
            model_name="fieldsyncoperation",
            old_name="smart_field_sync_order_status_idx",
            new_name="smart_fsync_order_status_idx",
        ),
        migrations.RenameIndex(
            model_name="fieldsyncoperation",
            old_name="smart_field_sync_technician_created_idx",
            new_name="smart_fsync_tech_created_idx",
        ),
        migrations.RenameIndex(
            model_name="technicianavailabilitywindow",
            old_name="smart_availability_company_tech_idx",
            new_name="smart_avail_comp_tech_idx",
        ),
        migrations.RenameIndex(
            model_name="scheduledvisit",
            old_name="smart_visit_technician_date_idx",
            new_name="smart_visit_tech_date_idx",
        ),
    ]
