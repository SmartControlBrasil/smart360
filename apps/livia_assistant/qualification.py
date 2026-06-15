from __future__ import annotations

import re


INVALID_GENERIC_VALUES = {
    "",
    "nao informado",
    "não informado",
    "nao informada",
    "não informada",
    "sim",
    "sim gostaria",
    "gostaria",
    "ok",
    "pode ser",
    "quero atendimento",
    "quero um atendimento",
    "preciso de atendimento",
    "preciso de suporte",
    "quero solicitar atendimento",
    "pode agendar uma visita",
    "quero agendar uma visita",
    "ja falei",
    "já falei",
    "quero um diagnóstico",
    "quero um diagnostico",
}

INVALID_COMPANY_OR_CITY_SNIPPETS = (
    "quero contato",
    "quero atendimento",
    "quero um atendimento",
    "quero solicitar atendimento",
    "quero um diagnóstico",
    "quero um diagnostico",
    "preciso de atendimento",
    "preciso de suporte",
    "falar com especialista",
    "pode agendar",
    "agendar uma visita",
    "choque termico",
    "choque térmico",
    "painel apagou",
    "maquina parou",
    "máquina parou",
    "camara climatica",
    "câmara climática",
    "nao gela",
    "não gela",
    "low pressure",
    "empresa de automacao para cuidar",
    "empresa de automação para cuidar",
)


def _normalize(value) -> str:
    return str(value or "").strip().lower()


def _is_invalid_generic(value) -> bool:
    normalized = _normalize(value)
    return normalized in INVALID_GENERIC_VALUES


def _is_valid_email(value) -> bool:
    if _is_invalid_generic(value):
        return False
    return bool(re.fullmatch(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", str(value).strip(), re.IGNORECASE))


def _is_valid_phone(value) -> bool:
    if _is_invalid_generic(value):
        return False
    digits = re.sub(r"\D", "", str(value or ""))
    return 10 <= len(digits) <= 15


def _is_valid_name(value) -> bool:
    normalized = _normalize(value)
    if normalized in INVALID_GENERIC_VALUES:
        return False
    return bool(re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]{1,149}", str(value or "").strip()))


def _is_valid_company_or_city(value) -> bool:
    normalized = _normalize(value)
    if normalized in INVALID_GENERIC_VALUES:
        return False
    if any(snippet in normalized for snippet in INVALID_COMPANY_OR_CITY_SNIPPETS):
        return False
    if normalized.startswith("de "):
        return False
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) >= 8:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9À-ÿ][A-Za-z0-9À-ÿ .&/'-]{1,179}", str(value or "").strip()))


def has_valid_name_field(capture) -> bool:
    return _is_valid_name(getattr(capture, "name", ""))


def has_valid_company_field(capture) -> bool:
    company = getattr(capture, "company", "") or getattr(capture, "company_name", "")
    return _is_valid_company_or_city(company)


def has_valid_city_field(capture) -> bool:
    return _is_valid_company_or_city(getattr(capture, "city", ""))


def has_valid_phone_field(capture) -> bool:
    return _is_valid_phone(getattr(capture, "phone", ""))


def has_valid_email_field(capture) -> bool:
    return _is_valid_email(getattr(capture, "email", ""))


def first_missing_required_field(capture) -> str:
    if not has_valid_name_field(capture):
        return "name"
    if not has_valid_company_field(capture):
        return "company"
    if not has_valid_city_field(capture):
        return "city"
    if not has_valid_phone_field(capture):
        return "phone"
    if not has_valid_email_field(capture):
        return "email"
    return ""


def is_lead_ready_for_notification(capture) -> bool:
    return not first_missing_required_field(capture)
