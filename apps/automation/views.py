import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import AutomationEvent, AutomationLog, WebhookEndpoint
from .services import create_or_update_lead_from_webhook


@csrf_exempt
@require_POST
def receive_webhook(request, slug):
    endpoint = WebhookEndpoint.objects.filter(slug=slug).first()
    if endpoint is None:
        return JsonResponse({"ok": False, "error": "Webhook endpoint não encontrado."}, status=404)

    if not endpoint.is_active:
        return JsonResponse({"ok": False, "error": "Webhook endpoint inativo."}, status=403)

    if endpoint.secret_token:
        token = (request.headers.get("X-Automation-Token") or request.GET.get("token") or "").strip()
        if token != endpoint.secret_token:
            return JsonResponse({"ok": False, "error": "Token inválido para este endpoint."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        AutomationLog.objects.create(
            source="webhook",
            workflow_name=endpoint.name,
            event_type="invalid_json",
            status=AutomationLog.Status.FAILED,
            error_message=f"JSON inválido: {exc}",
        )
        return JsonResponse({"ok": False, "error": "Payload JSON inválido."}, status=400)

    if not isinstance(payload, dict):
        AutomationLog.objects.create(
            source="webhook",
            workflow_name=endpoint.name,
            event_type="invalid_json",
            status=AutomationLog.Status.FAILED,
            error_message="Payload deve ser um objeto JSON.",
        )
        return JsonResponse({"ok": False, "error": "Payload JSON deve ser um objeto."}, status=400)

    event_type = str(payload.get("event_type") or "webhook.received")
    source = str(payload.get("source") or endpoint.slug)

    event = AutomationEvent.objects.create(
        event_type=event_type,
        source=source,
        payload=payload,
        processed=False,
    )

    log_response = {"event_id": event.id, "endpoint_slug": endpoint.slug}
    if event_type in {"lead.created", "xyron.lead.created"}:
        lead_result = create_or_update_lead_from_webhook(payload=payload, endpoint=endpoint)
        log_response.update(
            {
                "lead_id": lead_result["lead"].id,
                "lead_created": bool(lead_result["created"]),
            }
        )

    AutomationLog.objects.create(
        source="webhook",
        workflow_name=endpoint.name,
        event_type=event_type,
        status=AutomationLog.Status.SUCCESS,
        payload=payload,
        response=log_response,
    )

    return JsonResponse(
        {
            "ok": True,
            "event_id": event.id,
            "event_type": event.event_type,
            "source": event.source,
        }
    )
