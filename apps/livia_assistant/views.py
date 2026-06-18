import json
import re

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import LiviaChatForm
from .integrations import is_clear_technical_issue, is_lead_capture_intent, is_lead_data_message, is_web_system_project_text
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
    new_commercial_cycle = bool(
        locked_lead and service.is_new_commercial_cycle_message(message, conversation)
    )
    new_technical_cycle = service.is_new_technical_cycle_message(message)
    service.register_user_message(
        conversation,
        message,
        metadata={"source_page": source_page} if source_page else {},
    )
    locked_lead = locked_lead or service.get_locked_lead_capture(conversation)
    notified_commercial_append = _should_use_notified_append_reply(service, message, conversation)
    lead_capture = None
    lead_registered = False
    if locked_lead is not None and not new_commercial_cycle:
        collecting_lead = service.should_capture_post_qualified_update_for_conversation(message, conversation)
    elif locked_lead is not None and new_commercial_cycle:
        collecting_lead = True
    elif service._conversation_was_notified(conversation):
        collecting_lead = False
        locked_lead = locked_lead or service.get_locked_lead_capture(conversation)
    else:
        collecting_lead = service.should_start_contact_collection(conversation, message)
    if notified_commercial_append:
        collecting_lead = False
        locked_lead = locked_lead or service.get_locked_lead_capture(conversation)
    commercial_locked_followup = (
        locked_lead is not None
        and not new_commercial_cycle
        and not collecting_lead
        and service.detect_lead_intent(message)
        and not is_clear_technical_issue(service._normalize(message))
        and (
            notified_commercial_append
            or not service.should_capture_post_qualified_update_for_conversation(message, conversation)
        )
    )
    notified_commercial_followup = (
        notified_commercial_append
        or (
            service._conversation_was_notified(conversation)
            and not collecting_lead
            and service.detect_lead_intent(message)
            and not is_clear_technical_issue(service._normalize(message))
            and not service.should_capture_post_qualified_update_for_conversation(message, conversation)
        )
    )
    updating_lead = (
        collecting_lead
        or service.should_update_lead_capture(conversation, message)
        or commercial_locked_followup
        or notified_commercial_followup
        or notified_commercial_append
    )
    if updating_lead:
        extracted_data = service.extract_lead_data(message, conversation=conversation)
        if not collecting_lead:
            if service.needs_consultative_discovery_for_conversation(conversation, message) and is_lead_data_message(message):
                extracted_data = service.extract_spontaneous_contact_data(extracted_data)
            else:
                extracted_data = service.extract_notes_only_lead_data(extracted_data)
        if locked_lead is not None and not new_commercial_cycle:
            extracted_data = service.apply_post_qualified_expected_field(extracted_data, message, conversation)
        target_conversation = locked_lead.conversation if locked_lead is not None else conversation
        explicit_lead = None if new_commercial_cycle else locked_lead
        if (commercial_locked_followup or notified_commercial_followup or notified_commercial_append) and locked_lead is not None:
            collecting_lead = False
            explicit_lead = locked_lead
        elif notified_commercial_followup and locked_lead is None:
            locked_lead = service.get_locked_lead_capture(conversation)
            collecting_lead = False
            explicit_lead = locked_lead
        lead_capture = service.create_or_update_lead_capture(
            target_conversation,
            extracted_data,
            collecting_contact=collecting_lead,
            explicit_lead=explicit_lead,
        )
        lead_registered = bool((lead_capture.crm_reference or {}).get("notification_sent_this_turn"))

    if (
        lead_capture is None
        and notified_commercial_append
    ):
        locked = service.get_locked_lead_capture(conversation)
        if locked is not None:
            extracted_data = service.extract_notes_only_lead_data(
                service.extract_lead_data(message, conversation=conversation)
            )
            lead_capture = service.create_or_update_lead_capture(
                locked.conversation,
                extracted_data,
                collecting_contact=False,
                explicit_lead=locked,
            )
            lead_registered = bool((lead_capture.crm_reference or {}).get("notification_sent_this_turn"))

    if lead_capture is None and notified_commercial_append:
        locked = service.get_locked_lead_capture(conversation)
        if locked is not None:
            lead_capture = locked

    livia_response = service.generate_response(conversation, message)
    lead_detected = livia_response.lead_detected or lead_capture is not None

    if livia_response.handoff_recommended:
        service.create_handoff_request(conversation, "Fallback recomendou contato humano por urgência ou risco técnico.")

    starting_new_lead = new_commercial_cycle or (
        lead_capture is not None
        and locked_lead is not None
        and lead_capture.id != locked_lead.id
        and collecting_lead
    )
    is_technical = is_clear_technical_issue(service._normalize(message))
    discovery_pending = service.needs_consultative_discovery_for_conversation(conversation, message)
    prefer_provider_reply = (is_technical or discovery_pending) and not collecting_lead and not starting_new_lead
    post_qualified_collection = (
        collecting_lead and locked_lead is not None and not new_commercial_cycle
    )
    reply = _resolve_chat_reply(
        livia_response.reply,
        lead_registered,
        lead_capture,
        service,
        prefer_provider_reply=prefer_provider_reply,
        post_qualified_collection=post_qualified_collection,
        notified_commercial_append=notified_commercial_append,
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


def _has_explicit_contact_update(text):
    if re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text or "", re.IGNORECASE):
        return True
    normalized = str(text or "").strip().lower()
    if any(term in normalized for term in ("email", "e-mail")) and any(
        term in normalized for term in ("meu", "minha", "é", "e ", "informar", "passar", "atualizar")
    ):
        return True
    if re.search(r"\b(?:cidade|estou em|moro em|sou de)\s+", text or "", re.IGNORECASE):
        return True
    return False


def _should_use_notified_append_reply(service, message, conversation):
    normalized = service._normalize(message)
    if not (
        service._conversation_was_notified(conversation)
        and service._conversation_has_complete_contact(conversation)
        and service.detect_lead_intent(message)
        and not is_clear_technical_issue(normalized)
    ):
        return False
    if _has_explicit_contact_update(message):
        return False
    if service.should_capture_post_qualified_update_for_conversation(message, conversation) and any(
        term in normalized for term in ("email", "e-mail", "cidade")
    ) and any(term in normalized for term in ("quer", "posso", "informar", "passar", "saber", "qual")):
        return False
    return is_lead_capture_intent(normalized) or is_web_system_project_text(normalized)


def _resolve_chat_reply(
    default_reply,
    lead_registered,
    lead_capture,
    service,
    prefer_provider_reply=False,
    post_qualified_collection=False,
    notified_commercial_append=False,
):
    if lead_capture is None:
        return default_reply
    if prefer_provider_reply:
        return default_reply
    notification_sent_this_turn = bool(
        (lead_capture.crm_reference or {}).get("notification_sent_this_turn")
    )
    if (
        post_qualified_collection
        and service.should_send_qualified_reply(lead_capture)
        and service._conversation_was_notified(lead_capture.conversation)
        and not notification_sent_this_turn
    ):
        if notified_commercial_append:
            return service.build_lead_confirmation_reply(
                lead_capture,
                notification_sent_this_turn=False,
            )
        return default_reply
    if service.should_send_qualified_reply(lead_capture) or lead_registered:
        return service.build_lead_confirmation_reply(
            lead_capture,
            notification_sent_this_turn=notification_sent_this_turn or lead_registered,
        )
    return service.build_progressive_lead_reply(lead_capture)
