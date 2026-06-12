import re

from django.db import transaction

from apps.growth_engine.models import Lead, LeadSource
from apps.growth_engine.services.lead_service import LeadService


LEAD_DEFAULT_COMPANY_NAME = "Lead Webhook"
WEBHOOK_DEFAULT_SOURCE = "automation_webhook"


def _as_text(value, max_len=None):
    text = str(value or "").strip()
    if max_len is not None:
        return text[:max_len]
    return text


def _normalize_phone(value):
    return re.sub(r"\D+", "", str(value or ""))


def _append_notes(existing_notes, note_parts):
    incoming_note = "\n".join(part for part in note_parts if part).strip()
    if not incoming_note:
        return existing_notes
    if not existing_notes:
        return incoming_note
    if incoming_note in existing_notes:
        return existing_notes
    return f"{existing_notes}\n\n{incoming_note}"


def _get_or_create_lead_source(source_value):
    source_name = _as_text(source_value, 120) or "Automation Webhook"
    source, _ = LeadSource.objects.get_or_create(
        name=source_name,
        defaults={
            "source_type": LeadSource.SourceType.PARTNER,
            "description": "Lead recebido por webhook de automação.",
            "is_active": True,
        },
    )
    return source


def _find_existing_lead(email, phone, whatsapp):
    if email:
        lead = Lead.objects.filter(email__iexact=email).order_by("-id").first()
        if lead:
            return lead
    for contact in (whatsapp, phone):
        if not contact:
            continue
        lead = Lead.objects.filter(whatsapp=contact).order_by("-id").first()
        if lead:
            return lead
        lead = Lead.objects.filter(phone=contact).order_by("-id").first()
        if lead:
            return lead
    return None


@transaction.atomic
def create_or_update_lead_from_webhook(payload, endpoint=None):
    payload = payload or {}

    company_name = _as_text(payload.get("company_name") or payload.get("company"), 180) or LEAD_DEFAULT_COMPANY_NAME
    contact_name = _as_text(payload.get("contact_name") or payload.get("name"), 150)
    email = _as_text(payload.get("email")).lower()
    phone = _normalize_phone(payload.get("phone"))
    whatsapp = _normalize_phone(payload.get("whatsapp") or payload.get("phone"))
    website = _as_text(payload.get("website"), 200)
    city = _as_text(payload.get("city"), 100)
    state = _as_text(payload.get("state"), 100)
    segment = _as_text(payload.get("segment"), 120)
    product_interest = _as_text(payload.get("product_interest"), 180)
    message = _as_text(payload.get("message"))
    source_value = _as_text(payload.get("source"), 120) or WEBHOOK_DEFAULT_SOURCE

    existing_lead = _find_existing_lead(email=email, phone=phone, whatsapp=whatsapp)
    source = _get_or_create_lead_source(source_value)

    note_parts = [
        "Lead recebido via webhook de automação.",
        f"Endpoint: {endpoint.slug}" if endpoint else "",
        f"Origem informada: {source_value}",
        f"Interesse de produto: {product_interest}" if product_interest else "",
        f"Segmento: {segment}" if segment else "",
        message,
    ]

    metadata_payload = {
        "source": WEBHOOK_DEFAULT_SOURCE,
        "webhook_source": source_value,
        "webhook_endpoint": endpoint.slug if endpoint else "",
        "segment": segment,
        "product_interest": product_interest,
        "message": message,
    }

    if existing_lead is None:
        lead = LeadService.create_lead(
            user=None,
            validated_data={
                "company_name": company_name,
                "contact_name": contact_name,
                "email": email,
                "phone": phone[:30],
                "whatsapp": whatsapp[:30],
                "website": website,
                "city": city,
                "state": state,
                "source": source,
                "status": Lead.Status.NEW,
                "notes": _append_notes("", note_parts),
                "metadata": metadata_payload,
            },
        )
        return {"lead": lead, "created": True}

    merged_metadata = {**(existing_lead.metadata or {}), **metadata_payload}
    lead = LeadService.update_lead(
        lead=existing_lead,
        user=None,
        validated_data={
            "company_name": company_name or existing_lead.company_name,
            "contact_name": contact_name or existing_lead.contact_name,
            "email": email or existing_lead.email,
            "phone": phone[:30] or existing_lead.phone,
            "whatsapp": whatsapp[:30] or existing_lead.whatsapp,
            "website": website or existing_lead.website,
            "city": city or existing_lead.city,
            "state": state or existing_lead.state,
            "source": source or existing_lead.source,
            "status": existing_lead.status,
            "notes": _append_notes(existing_lead.notes, note_parts),
            "metadata": merged_metadata,
        },
    )
    return {"lead": lead, "created": False}
