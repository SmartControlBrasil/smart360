import uuid

from django.conf import settings
from django.db import models


class VoiceOpsProfile(models.Model):
    class Persona(models.TextChoices):
        TECHNICIAN = "technician", "Technician"
        MANAGER = "manager", "Manager"
        CLIENT = "client", "Client"

    class SttMode(models.TextChoices):
        BROWSER = "browser", "Browser"
        MANUAL = "manual", "Manual"
        FALLBACK = "fallback", "Fallback"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="voice_ops_profiles",
        null=True,
        blank=True,
    )
    persona = models.CharField(max_length=20, choices=Persona.choices, db_index=True)
    is_enabled = models.BooleanField(default=True)
    allow_tts = models.BooleanField(default=True)
    stt_mode = models.CharField(max_length=20, choices=SttMode.choices, default=SttMode.BROWSER)
    allowed_intents = models.JSONField(default=list, blank=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_voice_ops_profiles"
        ordering = ["persona", "company__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "persona"],
                name="uniq_ai_voice_ops_profile_company_persona",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_persona_display()} voice profile"


class VoiceInteraction(models.Model):
    class Persona(models.TextChoices):
        TECHNICIAN = "technician", "Technician"
        MANAGER = "manager", "Manager"
        CLIENT = "client", "Client"

    class Channel(models.TextChoices):
        PWA = "pwa", "PWA"
        DESKTOP = "desktop", "Desktop"
        PORTAL = "portal", "Portal"
        API = "api", "API"

    class InputMode(models.TextChoices):
        AUDIO = "audio", "Audio"
        TEXT = "text", "Text"
        HYBRID = "hybrid", "Hybrid"

    class TranscriptStatus(models.TextChoices):
        RECEIVED = "received", "Received"
        TRANSCRIBED = "transcribed", "Transcribed"
        FALLBACK = "fallback", "Fallback"
        FAILED = "failed", "Failed"

    class ActionStatus(models.TextChoices):
        RESPONSE_ONLY = "response_only", "Response Only"
        EXECUTED = "executed", "Executed"
        ROUTED = "routed", "Routed"
        BLOCKED = "blocked", "Blocked"
        FAILED = "failed", "Failed"

    id = models.BigAutoField(primary_key=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="voice_interactions",
        null=True,
        blank=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="voice_interactions",
        null=True,
        blank=True,
    )
    site = models.ForeignKey(
        "smart_system.OperationalSite",
        on_delete=models.SET_NULL,
        related_name="voice_interactions",
        null=True,
        blank=True,
    )
    persona = models.CharField(max_length=20, choices=Persona.choices, db_index=True)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.API)
    input_mode = models.CharField(max_length=20, choices=InputMode.choices, default=InputMode.AUDIO)
    locale = models.CharField(max_length=20, default="pt-BR")
    transcript_status = models.CharField(max_length=20, choices=TranscriptStatus.choices, default=TranscriptStatus.RECEIVED)
    transcript_text = models.TextField(blank=True)
    normalized_text = models.TextField(blank=True)
    detected_intent = models.CharField(max_length=80, blank=True, db_index=True)
    intent_confidence = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    entity_payload = models.JSONField(default=dict, blank=True)
    context_payload = models.JSONField(default=dict, blank=True)
    audio_metadata = models.JSONField(default=dict, blank=True)
    transcript_payload = models.JSONField(default=dict, blank=True)
    action_status = models.CharField(max_length=20, choices=ActionStatus.choices, default=ActionStatus.RESPONSE_ONLY)
    action_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=100, blank=True, db_index=True)
    correlation_id = models.CharField(max_length=100, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_voice_ops_interactions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["persona", "created_at"], name="ai_voice_persona_created_idx"),
            models.Index(fields=["company", "persona"], name="ai_voice_comp_persona_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.persona}:{self.detected_intent or 'unknown'}"
