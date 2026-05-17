from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


def seed_voice_profiles(apps, schema_editor):
    VoiceOpsProfile = apps.get_model("ai_voice_ops", "VoiceOpsProfile")
    defaults = {
        "technician": [
            "start_work_order",
            "complete_work_order",
            "report_issue",
            "add_part",
            "mark_checklist_nok",
            "request_help",
            "query_status",
            "query_schedule",
            "query_risk",
        ],
        "manager": ["query_summary", "query_status", "query_schedule", "query_risk"],
        "client": ["query_status", "query_schedule", "query_summary", "query_risk"],
    }
    for persona, intents in defaults.items():
        VoiceOpsProfile.objects.get_or_create(
            company=None,
            persona=persona,
            defaults={
                "is_enabled": True,
                "allow_tts": True,
                "stt_mode": "browser",
                "allowed_intents": intents,
                "config": {"locale": "pt-BR"},
            },
        )


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("companies", "0001_initial"),
        ("smart_system", "0006_field_offline_sync"),
    ]

    operations = [
        migrations.CreateModel(
            name="VoiceOpsProfile",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("persona", models.CharField(choices=[("technician", "Technician"), ("manager", "Manager"), ("client", "Client")], db_index=True, max_length=20)),
                ("is_enabled", models.BooleanField(default=True)),
                ("allow_tts", models.BooleanField(default=True)),
                ("stt_mode", models.CharField(choices=[("browser", "Browser"), ("manual", "Manual"), ("fallback", "Fallback")], default="browser", max_length=20)),
                ("allowed_intents", models.JSONField(blank=True, default=list)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="voice_ops_profiles", to="companies.company")),
            ],
            options={"db_table": "ai_voice_ops_profiles", "ordering": ["persona", "company__name"]},
        ),
        migrations.CreateModel(
            name="VoiceInteraction",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("public_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("persona", models.CharField(choices=[("technician", "Technician"), ("manager", "Manager"), ("client", "Client")], db_index=True, max_length=20)),
                ("channel", models.CharField(choices=[("pwa", "PWA"), ("desktop", "Desktop"), ("portal", "Portal"), ("api", "API")], default="api", max_length=20)),
                ("input_mode", models.CharField(choices=[("audio", "Audio"), ("text", "Text"), ("hybrid", "Hybrid")], default="audio", max_length=20)),
                ("locale", models.CharField(default="pt-BR", max_length=20)),
                ("transcript_status", models.CharField(choices=[("received", "Received"), ("transcribed", "Transcribed"), ("fallback", "Fallback"), ("failed", "Failed")], default="received", max_length=20)),
                ("transcript_text", models.TextField(blank=True)),
                ("normalized_text", models.TextField(blank=True)),
                ("detected_intent", models.CharField(blank=True, db_index=True, max_length=80)),
                ("intent_confidence", models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ("entity_payload", models.JSONField(blank=True, default=dict)),
                ("context_payload", models.JSONField(blank=True, default=dict)),
                ("audio_metadata", models.JSONField(blank=True, default=dict)),
                ("transcript_payload", models.JSONField(blank=True, default=dict)),
                ("action_status", models.CharField(choices=[("response_only", "Response Only"), ("executed", "Executed"), ("routed", "Routed"), ("blocked", "Blocked"), ("failed", "Failed")], default="response_only", max_length=20)),
                ("action_payload", models.JSONField(blank=True, default=dict)),
                ("response_payload", models.JSONField(blank=True, default=dict)),
                ("request_id", models.CharField(blank=True, db_index=True, max_length=100)),
                ("correlation_id", models.CharField(blank=True, db_index=True, max_length=100)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="voice_interactions", to="companies.company")),
                ("site", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="voice_interactions", to="smart_system.operationalsite")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="voice_interactions", to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "ai_voice_ops_interactions", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="voiceinteraction",
            index=models.Index(fields=["persona", "created_at"], name="ai_voice_interaction_persona_created_idx"),
        ),
        migrations.AddIndex(
            model_name="voiceinteraction",
            index=models.Index(fields=["company", "persona"], name="ai_voice_interaction_company_persona_idx"),
        ),
        migrations.AddConstraint(
            model_name="voiceopsprofile",
            constraint=models.UniqueConstraint(fields=("company", "persona"), name="uniq_ai_voice_ops_profile_company_persona"),
        ),
        migrations.RunPython(seed_voice_profiles, migrations.RunPython.noop),
    ]
