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
    "eu nao falei meu nome",
    "eu não falei meu nome",
    "nao falei meu nome",
    "não falei meu nome",
    "nao informei",
    "não informei",
    "nao passei",
    "não passei",
    "ainda não falei",
    "ainda nao falei",
}

INVALID_NAME_SNIPPETS = (
    "empresa",
    "camara",
    "câmara",
    "frigorifica",
    "frigorífica",
    "climatica",
    "climática",
    "equipamento",
    "maquina",
    "máquina",
    "ventilador",
    "gelo",
    "choque",
    "supermercado",
    "limpeza",
    "robo",
    "robô",
    "ar condicionado",
    "erro e2",
    "infraestrutura",
    "possui infraestrutura",
    "periodo noturno",
    "período noturno",
    "noturno",
)

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
    "camara frigorifica",
    "câmara frigorífica",
    "ar condicionado",
    "ar-condicionado",
    "erro e2",
    "nao gela",
    "não gela",
    "low pressure",
    "equipamento",
    "equipamennto",
    "que parou",
    "um equipamennto",
    "robo",
    "robô",
    "duno",
    "nao falei meu nome",
    "não falei meu nome",
    "eu nao falei",
    "eu não falei",
    "empresa de automacao para cuidar",
    "empresa de automação para cuidar",
    "todo o brasil",
    "brasil todo",
    "todo brasil",
    "nacional",
)


def _normalize(value) -> str:
    return str(value or "").strip().lower()


REPETITION_NOISE_PATTERNS = (
    r"\bja falei\b",
    r"\bjá falei\b",
    r"\bcomo falei\b",
    r"\beu ja falei\b",
    r"\beu já falei\b",
    r"\bconforme falei\b",
)


def strip_repetition_noise(value) -> str:
    cleaned = str(value or "").strip()
    for pattern in REPETITION_NOISE_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip(" ,.-")


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
    if len(digits) in {12, 13} and digits.startswith("55"):
        digits = digits[2:]
    return len(digits) in {10, 11}


def _is_valid_name(value) -> bool:
    normalized = _normalize(strip_repetition_noise(value))
    if normalized in INVALID_GENERIC_VALUES:
        return False
    if any(snippet in normalized for snippet in INVALID_NAME_SNIPPETS):
        return False
    if any(
        marker in normalized
        for marker in (
            "pode encaminhar",
            "quero orcamento",
            "quero orçamento",
            "quero um diagnostico",
            "quero um diagnóstico",
            "quero atendimento",
            "preciso de atendimento",
        )
    ):
        return False
    return bool(re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]{1,149}", strip_repetition_noise(value)))


def _is_valid_company_or_city(value) -> bool:
    cleaned = strip_repetition_noise(value)
    normalized = _normalize(cleaned)
    if normalized in INVALID_GENERIC_VALUES:
        return False
    if any(snippet in normalized for snippet in INVALID_COMPANY_OR_CITY_SNIPPETS):
        return False
    if normalized.startswith("de "):
        return False
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) >= 8:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9À-ÿ][A-Za-z0-9À-ÿ .&/'-]{1,179}", cleaned))


def has_valid_name_field(capture) -> bool:
    return _is_valid_name(getattr(capture, "name", ""))


def has_valid_company_field(capture) -> bool:
    company = getattr(capture, "company", "") or getattr(capture, "company_name", "")
    if not _is_valid_company_or_city(company):
        return False
    name = getattr(capture, "name", "") or ""
    if name and _normalize(company) == _normalize(name):
        return False
    return True


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
    if not has_valid_name_field(capture):
        return False
    if not has_valid_company_field(capture):
        return False
    if not has_valid_city_field(capture):
        return False
    if not has_valid_phone_field(capture):
        return False
    if not has_valid_email_field(capture):
        return False
    notes = _normalize(getattr(capture, "notes", ""))
    interest = _normalize(getattr(capture, "service_interest", ""))
    description = notes or interest
    if not description or description in INVALID_GENERIC_VALUES:
        return False
    return len(description) >= 3
