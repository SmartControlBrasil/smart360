from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedLeadData:
    name: str = ""
    company: str = ""
    phone: str = ""
    email: str = ""
    city: str = ""
    technical_context: str = ""
    service_interest: str = ""
    product_hint: str = ""


def extract_lead_data(text: str) -> ExtractedLeadData:
    raw = str(text or "").strip()
    normalized = raw.lower()

    email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", raw, re.IGNORECASE)
    phone_match = re.search(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}", raw)
    name_match = re.search(r"(?:meu nome é|me chamo|sou o|sou a|nome)\s+([A-Za-zÀ-ÿ ]{2,80})", raw, re.IGNORECASE)
    company_match = re.search(r"(?:empresa|da empresa|trabalho na|sou da)\s+([A-Za-z0-9À-ÿ .&-]{2,100})", raw, re.IGNORECASE)
    city_match = re.search(r"\b(?:cidade|estou em|em)\s+([A-Za-zÀ-ÿ ]{3,80})", raw, re.IGNORECASE)

    service_interest = ""
    if any(term in normalized for term in ("orcamento", "orçamento", "diagnostico", "diagnóstico", "suporte", "manutencao", "manutenção")):
        service_interest = "diagnóstico técnico"
    if any(term in normalized for term in ("duno", "dune", "hygibot", "robô de limpeza", "robo de limpeza")):
        service_interest = "Duno - robô de limpeza"

    product_hint = ""
    if any(term in normalized for term in ("duno", "dune", "hygibot")):
        product_hint = "hygibot"
    elif any(term in normalized for term in ("placa eletrônica", "placa eletronica", "microcontrolador", "iot")):
        product_hint = "engenharia_embarcada"

    technical_context = ""
    technical_markers = (
        "robô",
        "robo",
        "limpeza",
        "supermercado",
        "m²",
        "m2",
        "infraestrutura",
        "placa eletrônica",
        "placa eletronica",
        "retrofit",
        "diagnóstico",
        "diagnostico",
    )
    if any(marker in normalized for marker in technical_markers):
        technical_context = raw

    return ExtractedLeadData(
        name=(name_match.group(1).strip(" .,-") if name_match else "")[:150],
        company=(company_match.group(1).strip(" .,-") if company_match else "")[:180],
        phone=phone_match.group(0).strip() if phone_match else "",
        email=(email_match.group(0).strip() if email_match else "")[:180],
        city=(city_match.group(1).strip(" .,-") if city_match else "")[:120],
        technical_context=technical_context[:400],
        service_interest=service_interest[:180],
        product_hint=product_hint,
    )
