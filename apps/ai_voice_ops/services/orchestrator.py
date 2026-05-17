from __future__ import annotations

from django.db import transaction

from apps.ai_voice_ops.models import VoiceInteraction, VoiceOpsProfile
from apps.ai_voice_ops.services.actions import VoiceActionService
from apps.ai_voice_ops.services.context import VoiceContextResolver
from apps.ai_voice_ops.services.intents import VoiceIntentService
from apps.ai_voice_ops.services.transcription import VoiceTranscriptionService
from apps.observability_center.services.observability_service import SystemEventService
from shared_kernel.observability.context import get_correlation_id, get_request_id


class VoiceOpsOrchestrator:
    @classmethod
    def get_profile(cls, *, persona: str, company=None) -> VoiceOpsProfile | None:
        profile = None
        if company is not None:
            profile = VoiceOpsProfile.objects.filter(company=company, persona=persona).first()
        if profile is None:
            profile = VoiceOpsProfile.objects.filter(company__isnull=True, persona=persona).first()
        return profile

    @classmethod
    @transaction.atomic
    def process(
        cls,
        *,
        request,
        persona: str,
        channel: str,
        transcript_text: str = "",
        audio_metadata: dict | None = None,
        context_seed: dict | None = None,
        locale: str = "pt-BR",
        input_mode: str = VoiceInteraction.InputMode.AUDIO,
    ) -> dict:
        tenant_context = VoiceContextResolver.resolve_tenant_context(
            request=request,
            company_id=(context_seed or {}).get("company_id"),
            site_id=(context_seed or {}).get("site_id"),
        )
        company = tenant_context.get("company")
        site = tenant_context.get("site")
        profile = cls.get_profile(persona=persona, company=company)
        if profile and not profile.is_enabled:
            raise ValueError("VoiceOps desabilitado para esta persona.")

        request_id = get_request_id()
        correlation_id = get_correlation_id()
        SystemEventService.log_system_event(
            event_type="voice.input.received",
            source_module="ai_voice_ops",
            message="Voice input received.",
            entity_type="voice_persona",
            entity_id=persona,
            user=request.user,
            company=company,
            site=site,
            request_id=request_id,
            correlation_id=correlation_id,
            payload={"channel": channel, "input_mode": input_mode, "locale": locale},
        )

        transcription = VoiceTranscriptionService.transcribe(
            transcript_text=transcript_text,
            audio_metadata=audio_metadata,
            locale=locale,
        )
        SystemEventService.log_system_event(
            event_type="voice.transcribed",
            source_module="ai_voice_ops",
            message="Voice input transcribed.",
            entity_type="voice_persona",
            entity_id=persona,
            user=request.user,
            company=company,
            site=site,
            request_id=request_id,
            correlation_id=correlation_id,
            payload={"provider": transcription["provider"], "confidence": transcription["confidence"]},
        )

        parsed_intent = VoiceIntentService.parse(persona=persona, transcript_text=transcription["transcript_text"])
        SystemEventService.log_system_event(
            event_type="voice.intent.detected",
            source_module="ai_voice_ops",
            message="Voice intent detected.",
            entity_type="voice_persona",
            entity_id=persona,
            user=request.user,
            company=company,
            site=site,
            request_id=request_id,
            correlation_id=correlation_id,
            payload={"intent": parsed_intent.key, "confidence": parsed_intent.confidence},
        )

        resolved_context = VoiceContextResolver.resolve(
            request=request,
            persona=persona,
            parsed_intent=parsed_intent,
            context_seed=context_seed,
            tenant_context=tenant_context,
        )
        action_result = VoiceActionService.dispatch(
            request=request,
            persona=persona,
            parsed_intent=parsed_intent,
            transcript_text=transcription["transcript_text"],
            context_payload=resolved_context,
            context_seed=context_seed,
            tenant_context=tenant_context,
        )
        event_type = "voice.response.generated"
        if action_result["action_status"] == VoiceInteraction.ActionStatus.EXECUTED:
            event_type = "voice.action.executed"
        SystemEventService.log_system_event(
            event_type=event_type,
            source_module="ai_voice_ops",
            message="Voice response generated.",
            entity_type="voice_persona",
            entity_id=persona,
            user=request.user,
            company=company,
            site=site,
            request_id=request_id,
            correlation_id=correlation_id,
            payload={
                "intent": parsed_intent.key,
                "action_status": action_result["action_status"],
            },
        )

        interaction = VoiceInteraction.objects.create(
            user=request.user,
            company=company,
            site=site,
            persona=persona,
            channel=channel,
            input_mode=input_mode,
            locale=locale,
            transcript_status=transcription["status"],
            transcript_text=transcription["transcript_text"],
            normalized_text=transcription["transcript_text"].lower(),
            detected_intent=parsed_intent.key,
            intent_confidence=parsed_intent.confidence,
            entity_payload=parsed_intent.entities,
            context_payload=resolved_context,
            audio_metadata=audio_metadata or {},
            transcript_payload=transcription,
            action_status=action_result["action_status"],
            action_payload=action_result["action_payload"],
            response_payload={
                **action_result["response_payload"],
                "tts": {
                    "enabled": bool(profile.allow_tts) if profile else True,
                    "text": action_result["response_payload"].get("summary", ""),
                    "engine": "browser_speech_synthesis",
                },
            },
            request_id=request_id,
            correlation_id=correlation_id,
        )
        return {
            "interaction": interaction,
            "profile": profile,
            "transcription": transcription,
            "intent": {
                "key": parsed_intent.key,
                "confidence": parsed_intent.confidence,
                "entities": parsed_intent.entities,
                "is_action": parsed_intent.is_action,
            },
            "context": resolved_context,
            "response": interaction.response_payload,
            "action": {
                "status": interaction.action_status,
                "payload": interaction.action_payload,
            },
        }

