"""Envio da proposta comercial por e-mail (MVP), sem migrations."""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from apps.smart_site_factory.services.template_package import resolve_commercial_package_for_order

logger = logging.getLogger(__name__)


def _linked_lead_for_order(order):
    md = order.metadata if isinstance(order.metadata, dict) else {}
    lead_pk = md.get("lead_id")
    if lead_pk is None:
        return None
    try:
        from apps.growth_engine.models import Lead

        lead_pk_int = int(lead_pk)
    except (TypeError, ValueError):
        return None
    try:
        return Lead.objects.filter(pk=lead_pk_int).first()
    except Exception:
        return None


def resolve_proposal_recipient_email(order) -> str:
    """Prioridade: metadata client_email -> Lead -> requester."""
    md = order.metadata if isinstance(order.metadata, dict) else {}
    client = (md.get("client_email") or "").strip()
    if client:
        return client
    lead = _linked_lead_for_order(order)
    if lead is not None:
        em = (getattr(lead, "email", None) or "").strip()
        if em:
            return em
    if order.requester_id:
        return (getattr(order.requester, "email", None) or "").strip()
    return ""


def _proposal_price(order, commercial_package: dict | None) -> Decimal:
    fp = order.final_price or Decimal("0.00")
    if fp <= 0 and commercial_package and commercial_package.get("price_display"):
        try:
            package_price = Decimal(str(commercial_package["price_display"]))
            if package_price > 0:
                fp = package_price
        except (InvalidOperation, TypeError, ValueError):
            pass
    return fp


def build_proposal_email_context(*, order, request):
    """Mesma base de dados da view HTML da proposta (preco, pacote, prazos)."""
    md = order.metadata if isinstance(order.metadata, dict) else {}
    now = timezone.now()
    valid_until = now.date() + timedelta(days=7)
    commercial_package = resolve_commercial_package_for_order(order)
    fp = _proposal_price(order, commercial_package)
    half = (fp / Decimal("2")).quantize(Decimal("0.01"))
    balance = fp - half

    lead = _linked_lead_for_order(order)

    client_company = ""
    if order.company_id:
        client_company = order.company.name
    elif lead is not None and (lead.company_name or "").strip():
        client_company = lead.company_name.strip()
    else:
        client_company = md.get("client_company_name") or ""

    greeting_name = md.get("client_name") or ""
    if not greeting_name and order.requester_id:
        greeting_name = (order.requester.get_full_name() or order.requester.email or "").strip()
    if not greeting_name and lead is not None:
        greeting_name = (lead.contact_name or "").strip()

    rel = reverse("admin-shell:site-factory-order-proposal", kwargs={"pk": order.pk})
    proposal_absolute_url = request.build_absolute_uri(rel)

    return {
        "order": order,
        "commercial_package": commercial_package,
        "proposal_price": fp,
        "deposit_amount": half,
        "balance_amount": balance,
        "proposal_valid_until": valid_until,
        "proposal_generated_at": now,
        "linked_lead": lead,
        "client_company_display": client_company or order.niche.name,
        "greeting_name": greeting_name or "Cliente",
        "proposal_absolute_url": proposal_absolute_url,
    }


def send_site_order_proposal_email(*, order, request) -> tuple[bool, str]:
    """
    Envia e-mail HTML leve da proposta e atualiza SiteOrder.metadata em caso de sucesso.
    Retorna (sucesso, mensagem para exibir ao usuario).
    """
    to_email = resolve_proposal_recipient_email(order)
    if not to_email:
        return False, "Nenhum e-mail de destinatario encontrado. Informe o e-mail do cliente no pedido, no Lead ou use um solicitante com e-mail."
    try:
        validate_email(to_email)
    except ValidationError:
        return False, f"E-mail de destinatario invalido: {to_email}."

    ctx = build_proposal_email_context(order=order, request=request)
    subject = f"Proposta comercial — projeto #{order.id} | SMART Site Factory"

    try:
        html_body = render_to_string("admin_shell/emails/site_factory_proposal_email.html", ctx, request=request)
    except Exception as exc:
        logger.exception("Falha ao renderizar template de e-mail da proposta")
        return False, f"Erro ao montar o e-mail: {exc}"

    plain_body = strip_tags(html_body).strip() or subject

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@localhost"

    msg = EmailMultiAlternatives(subject=subject, body=plain_body, from_email=from_email, to=[to_email])
    msg.attach_alternative(html_body, "text/html")

    try:
        msg.send(fail_silently=False)
    except Exception as exc:
        logger.exception("Falha no envio SMTP da proposta")
        return False, f"Nao foi possivel enviar o e-mail. Verifique a configuracao de e-mail do servidor. ({exc})"

    om = dict(order.metadata) if isinstance(order.metadata, dict) else {}
    om["proposal_email_sent_at"] = timezone.now().isoformat()
    om["proposal_email_to"] = to_email
    om["proposal_email_status"] = "sent"
    order.metadata = om
    order.save(update_fields=["metadata", "updated_at"])

    return True, f"Proposta enviada para {to_email}."
