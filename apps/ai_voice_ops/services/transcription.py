from __future__ import annotations

import re

from apps.ai_voice_ops.models import VoiceInteraction


class VoiceTranscriptionService:
    NOISE_PATTERNS = [
        r"\[noise\]",
        r"\[inaudible\]",
        r"\(noise\)",
        r"\(inaudible\)",
    ]

    @classmethod
    def transcribe(
        cls,
        *,
        transcript_text: str = "",
        audio_metadata: dict | None = None,
        locale: str = "pt-BR",
    ) -> dict:
        audio_metadata = audio_metadata or {}
        source_text = (
            transcript_text
            or audio_metadata.get("browser_transcript")
            or audio_metadata.get("transcript_hint")
            or ""
        )
        cleaned = cls._clean_text(source_text)
        if cleaned:
            status = VoiceInteraction.TranscriptStatus.TRANSCRIBED
            provider = audio_metadata.get("provider") or "browser_speech_recognition"
            confidence = float(audio_metadata.get("confidence") or 0.92)
        else:
            status = VoiceInteraction.TranscriptStatus.FALLBACK
            provider = "fallback"
            confidence = 0.20
        return {
            "status": status,
            "provider": provider,
            "locale": locale or "pt-BR",
            "confidence": confidence,
            "transcript_text": cleaned,
            "raw_text": source_text,
        }

    @classmethod
    def _clean_text(cls, value: str) -> str:
        text = (value or "").strip()
        for pattern in cls.NOISE_PATTERNS:
            text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip()
        return text

