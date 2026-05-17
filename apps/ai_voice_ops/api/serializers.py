from rest_framework import serializers

from apps.ai_voice_ops.models import VoiceInteraction, VoiceOpsProfile
from apps.ai_voice_ops.services.intents import VoiceIntentService


class VoiceInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceInteraction
        fields = (
            "public_id",
            "persona",
            "channel",
            "input_mode",
            "locale",
            "transcript_status",
            "transcript_text",
            "detected_intent",
            "intent_confidence",
            "entity_payload",
            "context_payload",
            "action_status",
            "action_payload",
            "response_payload",
            "created_at",
            "updated_at",
        )


class VoiceOpsProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceOpsProfile
        fields = (
            "public_id",
            "company",
            "persona",
            "is_enabled",
            "allow_tts",
            "stt_mode",
            "allowed_intents",
            "config",
            "created_at",
            "updated_at",
        )


class VoiceProcessRequestSerializer(serializers.Serializer):
    persona = serializers.ChoiceField(choices=VoiceInteraction.Persona.choices)
    channel = serializers.ChoiceField(choices=VoiceInteraction.Channel.choices, default=VoiceInteraction.Channel.API)
    input_mode = serializers.ChoiceField(choices=VoiceInteraction.InputMode.choices, default=VoiceInteraction.InputMode.AUDIO)
    locale = serializers.CharField(required=False, default="pt-BR")
    transcript_text = serializers.CharField(required=False, allow_blank=True, default="")
    audio_metadata = serializers.JSONField(required=False, default=dict)
    context_seed = serializers.JSONField(required=False, default=dict)


class VoiceCatalogSerializer(serializers.Serializer):
    persona = serializers.CharField()
    intents = serializers.ListField(child=serializers.CharField())

    @classmethod
    def build_catalog(cls):
        return [
            {"persona": persona, "intents": VoiceIntentService.supported_intents(persona)}
            for persona in ["technician", "manager", "client"]
        ]

