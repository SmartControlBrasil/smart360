from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("ai_voice_ops", "0001_initial"),
    ]

    operations = [
        migrations.RenameIndex(
            model_name="voiceinteraction",
            old_name="ai_voice_interaction_persona_created_idx",
            new_name="ai_voice_persona_created_idx",
        ),
        migrations.RenameIndex(
            model_name="voiceinteraction",
            old_name="ai_voice_interaction_company_persona_idx",
            new_name="ai_voice_comp_persona_idx",
        ),
    ]
