from django.contrib import admin

from apps.ai_voice_ops.models import VoiceInteraction, VoiceOpsProfile


@admin.register(VoiceOpsProfile)
class VoiceOpsProfileAdmin(admin.ModelAdmin):
    list_display = ("persona", "company", "is_enabled", "allow_tts", "stt_mode", "updated_at")
    list_filter = ("persona", "is_enabled", "allow_tts", "stt_mode")
    search_fields = ("company__name",)


@admin.register(VoiceInteraction)
class VoiceInteractionAdmin(admin.ModelAdmin):
    list_display = (
        "persona",
        "channel",
        "user",
        "company",
        "site",
        "detected_intent",
        "transcript_status",
        "action_status",
        "created_at",
    )
    list_filter = ("persona", "channel", "transcript_status", "action_status", "detected_intent")
    search_fields = ("transcript_text", "normalized_text", "detected_intent", "user__email")
    readonly_fields = ("public_id", "request_id", "correlation_id", "created_at", "updated_at")

