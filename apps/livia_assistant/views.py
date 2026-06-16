import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import LiviaChatForm
from .models import LiviaLeadCapture, LiviaMessage
from .services import LiviaAssistantService


@csrf_exempt
@require_POST
def chat(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Payload JSON inválido."}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"error": "Payload JSON deve ser um objeto."}, status=400)

    raw_message = str(payload.get("message") or "").strip()
    if not raw_message:
        return JsonResponse({"error": "Informe uma mensagem para a Lívia."}, status=400)
    if len(raw_message) > 2000:
        return JsonResponse({"error": "Mensagem muito longa. Envie até 2000 caracteres."}, status=400)

    form = LiviaChatForm(payload)
    if not form.is_valid():
        return JsonResponse({"error": "Payload inválido.", "details": form.errors}, status=400)

    message = form.cleaned_data["message"].strip()
    source_page = form.cleaned_data.get("source_page", "")
    session_key = form.cleaned_data.get("session_key") or _get_or_create_session_key(request)

    service = LiviaAssistantService()
    conversation = service.get_or_create_conversation(
        session_key=session_key,
        source_page=source_page,
        current_message=message,
    )
    locked_lead = service.get_locked_lead_capture(conversation)
    new_technical_cycle = service.is_new_technical_cycle_message(message)
    service.register_user_message(
        conversation,
        message,
        metadata={"source_page": source_page} if source_page else {},
    )
    lead_capture = None
    lead_registered = False
    if locked_lead is not None and not new_technical_cycle:
        collecting_lead = service.should_capture_post_qualified_update_for_conversation(message, conversation)
    else:
        collecting_lead = service.is_lead_collection_active(conversation)
        if not collecting_lead:
            collecting_lead = service.should_collect_explicit_contact_message(message)
    updating_lead = collecting_lead or service.should_update_lead_capture(conversation, message)
    if updating_lead:
        extracted_data = service.extract_lead_data(message, conversation=conversation)
        if not collecting_lead:
            extracted_data = service.extract_notes_only_lead_data(extracted_data)
        if locked_lead is not None and not new_technical_cycle:
            extracted_data = service.apply_post_qualified_expected_field(extracted_data, message, conversation)
        target_conversation = conversation
        if locked_lead is not None and not new_technical_cycle:
            target_conversation = locked_lead.conversation
        lead_capture = service.create_or_update_lead_capture(
            target_conversation,
            extracted_data,
            collecting_contact=collecting_lead,
            explicit_lead=locked_lead if locked_lead is not None and not new_technical_cycle else None,
        )
        lead_registered = lead_capture.operational_status == LiviaLeadCapture.OperationalStatus.SENT_TO_CRM

    livia_response = service.generate_response(conversation, message)
    lead_detected = livia_response.lead_detected or lead_capture is not None

    if livia_response.handoff_recommended:
        service.create_handoff_request(conversation, "Fallback recomendou contato humano por urgência ou risco técnico.")

    reply = _resolve_chat_reply(
        livia_response.reply,
        lead_registered,
        lead_capture,
        service,
        prefer_provider_reply=locked_lead is not None and not new_technical_cycle,
    )
    if lead_capture is not None and reply != livia_response.reply:
        last_assistant = (
            conversation.messages.filter(role=LiviaMessage.Role.ASSISTANT)
            .order_by("-created_at", "-id")
            .first()
        )
        if last_assistant is not None:
            last_assistant.content = reply
            last_assistant.save(update_fields=["content"])

    return JsonResponse(
        {
            "conversation_id": conversation.id,
            "reply": reply,
            "lead_detected": lead_detected,
            "handoff_recommended": livia_response.handoff_recommended,
            "session_key": conversation.session_key,
            "lead_registered": lead_registered,
        }
    )


def _get_or_create_session_key(request):
    if not hasattr(request, "session"):
        return ""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _resolve_chat_reply(default_reply, lead_registered, lead_capture, service, prefer_provider_reply=False):
    if lead_capture is None:
        return default_reply
    if prefer_provider_reply:
        return default_reply
    if service.should_send_qualified_reply(lead_capture) or lead_registered:
        return service.build_qualified_lead_reply(lead_capture)
    return service.build_progressive_lead_reply(lead_capture)
