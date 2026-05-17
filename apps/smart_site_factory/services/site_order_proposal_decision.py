"""Aprovacao/rejeicao de proposta comercial via SiteOrder.metadata (sem migrations)."""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone

logger = logging.getLogger(__name__)


def _metadata_dict(order) -> dict[str, Any]:
    raw = getattr(order, "metadata", None)
    if raw is None or not isinstance(raw, dict):
        return {}
    return dict(raw)


def _actor_stamp(user) -> str:
    email = (getattr(user, "email", None) or "").strip()
    if email:
        return email
    return str(getattr(user, "pk", "") or "")


def _linked_lead_for_order(order):
    md = _metadata_dict(order)
    lead_pk = md.get("lead_id")
    if lead_pk is None:
        return None
    try:
        lead_id = int(lead_pk)
    except (TypeError, ValueError):
        return None
    try:
        from apps.growth_engine.models import Lead

        return Lead.objects.filter(pk=lead_id).first()
    except Exception:
        return None


def apply_proposal_approval(*, order, user) -> tuple[bool, str]:
    md = _metadata_dict(order)
    cur = (md.get("proposal_status") or "").strip().lower()
    if cur in ("approved", "rejected"):
        return False, "Esta proposta ja foi aprovada ou rejeitada."

    md = {**md}
    md["proposal_status"] = "approved"
    md["proposal_approved_at"] = timezone.now().isoformat()
    md["proposal_approved_by"] = _actor_stamp(user)
    md["commercial_status"] = "proposal_approved"
    order.metadata = md
    order.save(update_fields=["metadata", "updated_at"])

    lead = _linked_lead_for_order(order)
    if lead is not None:
        try:
            from apps.growth_engine.models import Lead

            lead.status = Lead.Status.WON
            lead.save(update_fields=["status", "updated_at"])
        except Exception as exc:
            logger.warning("Nao foi possivel atualizar Lead para won: %s", exc)

    return True, "Proposta aprovada."


def apply_proposal_rejection(*, order, user) -> tuple[bool, str]:
    md = _metadata_dict(order)
    cur = (md.get("proposal_status") or "").strip().lower()
    if cur in ("approved", "rejected"):
        return False, "Esta proposta ja foi aprovada ou rejeitada."

    md = {**md}
    md["proposal_status"] = "rejected"
    md["proposal_rejected_at"] = timezone.now().isoformat()
    md["proposal_rejected_by"] = _actor_stamp(user)
    md["commercial_status"] = "proposal_rejected"
    order.metadata = md
    order.save(update_fields=["metadata", "updated_at"])

    lead = _linked_lead_for_order(order)
    if lead is not None:
        try:
            from apps.growth_engine.models import Lead

            lead.status = Lead.Status.LOST
            lead.save(update_fields=["status", "updated_at"])
        except Exception as exc:
            logger.warning("Nao foi possivel atualizar Lead para lost: %s", exc)

    return True, "Proposta rejeitada."
