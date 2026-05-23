"""Constantes e utilitários leves para exibição de CommercialProposal."""

from typing import Optional


MARKETPLACE_ECOM_ORIGIN = "marketplace_ecom"


def commercial_proposal_is_marketplace_origin(proposal) -> bool:
    md = getattr(proposal, "metadata", None) or {}
    # Vínculo explícito ao lead criado pelo fluxo técnico B2B
    if md.get("marketplace_lead_id") is not None:
        return True
    origin_f = (getattr(proposal, "origin", None) or "").strip()
    if origin_f == MARKETPLACE_ECOM_ORIGIN:
        return True
    if md.get("proposal_origin") == MARKETPLACE_ECOM_ORIGIN or md.get("source") == MARKETPLACE_ECOM_ORIGIN:
        return True
    return False


def resolve_marketplace_lead_id_for_detail_link(proposal) -> Optional[int]:
    md = getattr(proposal, "metadata", None) or {}
    raw = md.get("marketplace_lead_id")
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    if getattr(proposal, "lead_id", None):
        return int(proposal.lead_id)
    return None


def marketplace_proposal_suggested_email_intro(proposal) -> str:
    md = getattr(proposal, "metadata", None) or {}
    product = md.get("product_title") or md.get("product_slug") or (proposal.service_interest or "").strip() or "(item solicitado)"
    company = proposal.company_name
    proposal_no = proposal.proposal_number

    lines = [
        f"Prezados da {company},",
        "",
        "Esta comunicação faz referência ao orçamento comercial solicitado pelo canal Marketplace técnico B2B da Smart360, "
        "onde foi registrado o pedido sob consulta de catálogo. A seguir compartilhamos a proposta comercial em minuta.",
        "",
        f"Referência interna da proposta: {proposal_no}.",
        f"Linha / solução de interesse: {product}.",
        "",
        "Validamos valores, disponibilidade, prazo de entrega/execução e condições técnicas com o time antes do envio definitivo ao cliente.",
        "",
        "Atenciosamente,",
    ]
    return "\n".join(lines)
