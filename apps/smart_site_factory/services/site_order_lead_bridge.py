"""Ponte comercial MVP entre SiteOrder (Smart Site Factory) e Lead (Growth Engine), sem migrations."""

from __future__ import annotations

from django.db import transaction

from ..models import SiteOrder
from .template_package import extract_package_catalog


def _lead_metadata_for_order(order: SiteOrder) -> dict:
    tpl = order.selected_template
    md_order = order.metadata or {}
    order_price = str(order.final_price)
    snap = md_order.get("package_snapshot") if isinstance(md_order.get("package_snapshot"), dict) else {}
    if snap:
        pkg_code = str(snap.get("package_code") or "").strip()
        pkg_name = str(snap.get("commercial_name") or "").strip()
        pkg_tier = str(snap.get("tier") or "").strip()
    elif tpl is not None:
        cat = extract_package_catalog(tpl)
        pkg_code = cat.get("package_code") or ""
        pkg_name = cat.get("commercial_name") or tpl.name
        pkg_tier = cat.get("tier") or ""
    else:
        pkg_code = ""
        pkg_name = ""
        pkg_tier = ""
    return {
        "site_order_id": order.id,
        "site_order_public_id": str(order.public_id),
        "source_module": "smart_site_factory",
        "estimated_value": order_price,
        "selected_template": tpl.name if tpl else "",
        "selected_template_slug": tpl.slug if tpl else "",
        "package_code": pkg_code,
        "package_name": pkg_name,
        "package_tier": pkg_tier,
        "package_price": order_price,
    }


def _order_contact_payload(order: SiteOrder) -> dict:
    md = order.metadata or {}
    company_name = ""
    if order.company_id:
        company_name = order.company.name
    if not company_name:
        company_name = (md.get("client_company_name") or "").strip()
    if not company_name:
        company_name = f"Site Factory — pedido #{order.id}"

    contact_name = (md.get("client_name") or "").strip()
    if not contact_name and order.requester_id:
        contact_name = (order.requester.get_full_name() or "").strip()
    if not contact_name and order.requester_id:
        contact_name = order.requester.email or ""

    email = (md.get("client_email") or "").strip()
    if not email and order.requester_id:
        email = (order.requester.email or "").strip()

    phone = (md.get("client_phone") or "").strip()
    return {
        "company_name": company_name[:180],
        "contact_name": contact_name[:150],
        "email": email[:254] if email else "",
        "phone": phone[:30],
    }


def upsert_lead_from_site_order(*, order: SiteOrder, user):
    """
    Cria ou atualiza um Lead vinculado ao SiteOrder, persistindo metadados nos dois lados.
    Levanta ValueError com mensagem amigável em caso de falha recuperável.
    """
    try:
        from apps.growth_engine.models import Lead
        from apps.growth_engine.services.lead_service import LeadScoringService, LeadService
    except Exception as exc:  # pragma: no cover - app opcional
        raise ValueError("Modulo Growth Engine nao esta disponivel.") from exc

    contact = _order_contact_payload(order)
    bridge = _lead_metadata_for_order(order)

    with transaction.atomic():
        lead = None
        md_order = order.metadata or {}
        lead_pk = md_order.get("lead_id")
        if lead_pk is not None:
            try:
                lead_pk_int = int(lead_pk)
            except (TypeError, ValueError):
                lead_pk_int = None
            if lead_pk_int:
                lead = Lead.objects.filter(pk=lead_pk_int).first()

        if lead is None:
            lead = Lead.objects.filter(metadata__site_order_id=order.id).first()

        merged_lead_meta = {**(lead.metadata if lead else {}), **bridge}

        if lead is None:
            validated = {
                "company_name": contact["company_name"],
                "contact_name": contact["contact_name"],
                "email": contact["email"],
                "phone": contact["phone"],
                "whatsapp": "",
                "website": "",
                "city": "",
                "state": "",
                "niche": order.niche,
                "source": None,
                "campaign": None,
                "status": Lead.Status.PROPOSAL,
                "notes": f"Oportunidade gerada a partir do pedido Smart Site Factory #{order.id} (public_id {order.public_id}).",
                "metadata": merged_lead_meta,
            }
            lead = LeadService.create_lead(user=user, validated_data=validated)
        else:
            merged_lead_meta = {**(lead.metadata or {}), **bridge}
            lead.company_name = contact["company_name"]
            lead.contact_name = contact["contact_name"]
            lead.email = contact["email"]
            lead.phone = contact["phone"]
            lead.niche = order.niche
            lead.status = Lead.Status.PROPOSAL
            lead.metadata = merged_lead_meta
            notes_extra = f"Atualizado via pedido Smart Site Factory #{order.id}."
            if notes_extra not in (lead.notes or ""):
                lead.notes = f"{lead.notes}\n{notes_extra}".strip()
            lead.score = LeadScoringService.calculate_score(lead=lead)
            lead.save()

        om = dict(order.metadata or {})
        om["lead_id"] = lead.id
        om["lead_public_id"] = str(lead.public_id)
        om["commercial_status"] = "opportunity_created"
        order.metadata = om
        order.save(update_fields=["metadata", "updated_at"])

    return lead
