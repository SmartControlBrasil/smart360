from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("ai_optimization_loop", "0001_initial"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="optimizationproposal",
            old_name="ai_opt_proposal_company_status_idx",
            new_name="ai_opt_prop_comp_status_idx",
        ),
        migrations.RenameIndex(
            model_name="optimizationproposal",
            old_name="ai_opt_proposal_target_type_idx",
            new_name="ai_opt_prop_target_prop_idx",
        ),
    ]
