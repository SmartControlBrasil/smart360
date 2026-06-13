import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import LiviaChatForm
from .models import LiviaLeadCapture
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
    conversation = service.get_or_create_conversation(session_key=session_key, source_page=source_page)
    service.register_user_message(
        conversation,
        message,
        metadata={"source_page": source_page} if source_page else {},
    )
    livia_response = service.generate_response(conversation, message)

    lead_detected = livia_response.lead_detected
    lead_registered = False
    lead_capture = None
    if lead_detected:
        extracted_data = service.extract_lead_data(message)
        lead_capture = service.create_or_update_lead_capture(conversation, extracted_data)
        lead_registered = lead_capture.operational_status == LiviaLeadCapture.OperationalStatus.SENT_TO_CRM

    if livia_response.handoff_recommended:
        service.create_handoff_request(conversation, "Fallback recomendou contato humano por urgência ou risco técnico.")

    return JsonResponse(
        {
            "conversation_id": conversation.id,
            "reply": _resolve_chat_reply(livia_response.reply, lead_registered, lead_capture),
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


def _resolve_chat_reply(default_reply, lead_registered, lead_capture):
    if not lead_registered:
        return default_reply

    if lead_capture and not lead_capture.email:
        return default_reply
    if lead_capture and not _has_problem_context(lead_capture.notes):
        return default_reply
    return "Perfeito, registrei seu interesse e encaminhei para um especialista da Smart Control Brasil. Em breve entraremos em contato."


def _has_problem_context(notes):
    normalized = str(notes or "").strip().lower()
    return any(
        term in normalized
        for term in (
            "problema",
            "objetivo",
            "falha",
            "falhas",
            "parada",
            "paradas",
            "diagnostico",
            "diagnóstico",
            "suporte",
            "linha",
            "maquina",
            "máquina",
        )
    )
