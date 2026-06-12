import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.growth_engine.models import Lead, LeadSource
from apps.growth_engine.services.lead_service import LeadService


def _find_duplicate_lead(*, source_obj, email, phone, company_name, contact_name):
    if email:
        lead = Lead.objects.filter(email__iexact=email, source=source_obj).order_by("-id").first()
        if lead:
            return lead

    if not email and phone:
        lead = Lead.objects.filter(phone=phone, source=source_obj).order_by("-id").first()
        if lead:
            return lead

    if not email and not phone and (company_name or contact_name):
        queryset = Lead.objects.filter(source=source_obj)
        if company_name:
            queryset = queryset.filter(company_name__iexact=company_name)
        if contact_name:
            queryset = queryset.filter(contact_name__iexact=contact_name)
        lead = queryset.order_by("-id").first()
        if lead:
            return lead

    return None


@csrf_exempt
@require_POST
def receive_n8n_lead(request):
    expected_token = str(getattr(settings, "N8N_WEBHOOK_TOKEN", "") or "").strip()
    received_token = str(request.headers.get("X-N8N-TOKEN") or "").strip()

    if not expected_token or received_token != expected_token:
        return JsonResponse({"ok": False, "error": "Token inválido."}, status=403)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Payload JSON inválido."}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({"ok": False, "error": "Payload deve ser um objeto JSON."}, status=400)

    contact_name = str(payload.get("name") or "").strip()[:150]
    company_name = str(payload.get("company") or "").strip()[:180]
    if not company_name:
        company_name = contact_name
    if not company_name:
        return JsonResponse(
            {"ok": False, "error": "Informe pelo menos 'company' ou 'name' para criar o lead."},
            status=400,
        )

    source_name = str(payload.get("source") or "n8n").strip()[:120] or "n8n"
    source_obj, _ = LeadSource.objects.get_or_create(
        name=source_name,
        defaults={
            "source_type": LeadSource.SourceType.PARTNER,
            "description": "Origem de leads recebidos via integração n8n.",
            "is_active": True,
        },
    )
    email = str(payload.get("email") or "").strip().lower()
    phone = str(payload.get("phone") or "").strip()[:30]

    duplicate = _find_duplicate_lead(
        source_obj=source_obj,
        email=email,
        phone=phone,
        company_name=company_name,
        contact_name=contact_name,
    )
    if duplicate is not None:
        return JsonResponse(
            {"ok": True, "id": duplicate.id, "created": False, "duplicate": True},
            status=200,
        )

    segment = str(payload.get("segment") or "").strip()
    interest = str(payload.get("interest") or "").strip()
    notes = str(payload.get("notes") or "").strip()
    note_parts = [notes] if notes else []
    if segment:
        note_parts.append(f"Segmento: {segment}")
    if interest:
        note_parts.append(f"Interesse: {interest}")

    lead = LeadService.create_lead(
        user=None,
        validated_data={
            "company_name": company_name,
            "contact_name": contact_name,
            "email": email,
            "phone": phone,
            "whatsapp": phone,
            "city": str(payload.get("city") or "").strip()[:100],
            "state": str(payload.get("state") or "").strip()[:100],
            "source": source_obj,
            "status": Lead.Status.NEW,
            "notes": "\n".join(part for part in note_parts if part),
            "metadata": {
                "source": "n8n_webhook",
                "segment": segment,
                "interest": interest,
                "raw_source": source_name,
            },
        },
    )

    return JsonResponse({"ok": True, "id": lead.id, "created": True, "duplicate": False}, status=201)
