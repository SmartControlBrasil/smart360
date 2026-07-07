from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from django.core.cache import cache


HONEYPOT_FIELD = "website"

SUSPICIOUS_CONTACT_TERMS = (
    "casino",
    "cassino",
    "betting",
    "bet",
    "crypto",
    "bitcoin",
    "loan",
    "viagra",
    "seo backlinks",
    "backlink",
    "pornography",
    "adult",
    "hacked",
    "free money",
)

GENERIC_PRAISE_PHRASES = (
    "impressed",
    "nicely design",
    "great user experience",
    "just browsing",
    "just had to drop",
    "have a great day",
    "love your site",
    "love your website",
    "great layout",
    "wonderful site",
    "beautiful website",
    "nice website",
    "drop a message",
)

COMMERCIAL_INTERESTS = {
    "automacao",
    "robotica",
    "iot_dados",
    "produtos",
    "software",
    "retrofit",
    "retrofit_suporte",
    "manutencao",
    "acionamentos",
    "supervisorio",
    "energia",
}

COMMERCIAL_INTENT_TERMS = (
    "orçamento",
    "orcamento",
    "proposta",
    "projeto",
    "integração",
    "integracao",
    "automação",
    "automacao",
    "máquina",
    "maquina",
    "painel",
    "clp",
    "ihm",
    "sistema",
    "dashboard",
    "retrofit",
    "manutenção",
    "manutencao",
    "visita",
    "diagnóstico",
    "diagnostico",
    "need",
    "quote",
    "project",
    "integration",
    "automation",
    "machine",
    "timeline",
    "prazo",
    "budget",
    "proposal",
    "robot",
    "robô",
    "robo",
    "plc",
    "scada",
)

LINK_RE = re.compile(r"(https?://|www\.)", re.IGNORECASE)
DOMAIN_IN_TEXT_RE = re.compile(
    r"\b[a-z0-9][a-z0-9-]*\.(?:com|com\.br|net|org|io)\b",
    re.IGNORECASE,
)
REPEATED_CHARS_RE = re.compile(r"(.)\1{7,}")
TRAILING_JUNK_RE = re.compile(r"[!.\s]+([a-z0-9]{6,14})\s*$", re.IGNORECASE)
EMAIL_LOCAL_DIGITS_RE = re.compile(r"^\d{3,}|(?<=[a-z])\d{3,}[a-z]*$", re.IGNORECASE)

SPAM_SCORE_THRESHOLD = 45
SUSPICIOUS_SCORE_THRESHOLD = 25

DEFAULT_RATE_LIMIT = 5
DEFAULT_RATE_WINDOW_SECONDS = 900


class ContactSubmissionClass(str, Enum):
    CLEAN = "clean"
    SUSPICIOUS = "suspicious"
    SPAM = "spam"


@dataclass(frozen=True)
class ContactSpamVerdict:
    classification: ContactSubmissionClass
    score: int
    reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def should_send_notification(self) -> bool:
        return self.classification == ContactSubmissionClass.CLEAN

    @property
    def should_send_review_notification(self) -> bool:
        return self.classification == ContactSubmissionClass.SUSPICIOUS


def partial_ip(ip: str) -> str:
    ip = (ip or "").strip()
    if not ip:
        return ""
    if ":" in ip:
        parts = ip.split(":")
        if len(parts) > 4:
            return ":".join(parts[:4]) + ":*"
        return ip
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.*"
    return ip[:12] + "..."


def _cache_rate_key(ip: str) -> str:
    digest = hashlib.sha256(ip.encode("utf-8")).hexdigest()[:16]
    return f"institutional:contact:rate:{digest}"


def is_contact_rate_limited(
    ip: str,
    *,
    limit: int = DEFAULT_RATE_LIMIT,
    window_seconds: int = DEFAULT_RATE_WINDOW_SECONDS,
) -> bool:
    if not ip:
        return False
    key = _cache_rate_key(ip)
    count = cache.get(key, 0)
    if count >= limit:
        return True
    cache.set(key, count + 1, window_seconds)
    return False


def _normalize_message(message: str) -> str:
    return re.sub(r"\s+", " ", (message or "").strip())


def _digits_only(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _names_too_similar(contact_name: str, company: str) -> bool:
    if not company or not contact_name:
        return False
    normalized_name = contact_name.strip().lower()
    normalized_company = company.strip().lower()
    if normalized_company == normalized_name:
        return True
    first_name = normalized_name.split()[0] if normalized_name.split() else ""
    if first_name and normalized_company == first_name and len(normalized_company) <= 4:
        return True
    return False


def _looks_like_trailing_junk(token: str) -> bool:
    lowered = token.lower()
    if not re.fullmatch(r"[a-z0-9]{6,14}", lowered):
        return False
    vowels = sum(1 for char in lowered if char in "aeiou")
    has_digits = any(char.isdigit() for char in lowered)
    return has_digits and vowels <= 2


def _has_commercial_intent(message: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in COMMERCIAL_INTENT_TERMS)


def _score_submission(data: Mapping[str, Any]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    contact_name = str(data.get("contact_name", "")).strip()
    company = str(data.get("company", "")).strip()
    whatsapp = str(data.get("whatsapp", "")).strip()
    email = str(data.get("email", "")).strip()
    message = str(data.get("message", "")).strip()
    interest = (
        str(data.get("interest", "")).strip()
        or str(data.get("primary_interest", "")).strip()
    )
    main_problem = str(data.get("main_problem", "")).strip()
    honeypot = str(data.get(HONEYPOT_FIELD, "")).strip()

    if honeypot:
        return 100, ["honeypot_filled"]

    if not contact_name or not email or not message:
        return 100, ["missing_required_fields"]

    useful_message = _normalize_message(message)
    if len(useful_message) < 10:
        score += 40
        reasons.append("message_too_short")

    link_count = len(LINK_RE.findall(message)) + len(DOMAIN_IN_TEXT_RE.findall(message))
    if link_count > 5:
        score += 35
        reasons.append("too_many_links")

    lowered = useful_message.lower()
    if any(term in lowered for term in SUSPICIOUS_CONTACT_TERMS):
        score += 45
        reasons.append("blocked_term")

    if REPEATED_CHARS_RE.search(lowered):
        score += 30
        reasons.append("repeated_characters")

    unique_chars = set(lowered)
    if len(lowered) >= 60 and len(unique_chars) <= 8:
        score += 30
        reasons.append("low_entropy_message")

    praise_hits = sum(1 for phrase in GENERIC_PRAISE_PHRASES if phrase in lowered)
    if praise_hits >= 3:
        score += 35
        reasons.append("generic_praise_message")
    elif praise_hits >= 2:
        score += 25
        reasons.append("generic_praise_message")

    trailing_match = TRAILING_JUNK_RE.search(useful_message)
    if trailing_match and _looks_like_trailing_junk(trailing_match.group(1)):
        score += 30
        reasons.append("trailing_random_token")

    if company and len(company) <= 3:
        score += 15
        reasons.append("company_too_short")

    if _names_too_similar(contact_name, company):
        score += 20
        reasons.append("company_similar_to_name")

    whatsapp_digits = _digits_only(whatsapp)
    if whatsapp and len(whatsapp_digits) < 10:
        score += 15
        reasons.append("whatsapp_too_short")

    if email and "@" in email:
        local_part = email.split("@", 1)[0]
        if EMAIL_LOCAL_DIGITS_RE.search(local_part):
            score += 10
            reasons.append("email_local_suspicious_pattern")

    if interest in COMMERCIAL_INTERESTS and not main_problem:
        if not _has_commercial_intent(useful_message):
            if praise_hits >= 1:
                score += 20
                reasons.append("commercial_interest_without_context")
            elif len(useful_message.split()) <= 18:
                score += 10
                reasons.append("commercial_interest_without_context")

    return score, reasons


def classify_contact_submission(data: Mapping[str, Any]) -> ContactSpamVerdict:
    """
    Classifica envios do formulário institucional.

    Future hook: validar CAPTCHA/Turnstile antes de chamar esta função.
    """
    score, reasons = _score_submission(data)
    if score >= SPAM_SCORE_THRESHOLD:
        classification = ContactSubmissionClass.SPAM
    elif score >= SUSPICIOUS_SCORE_THRESHOLD:
        classification = ContactSubmissionClass.SUSPICIOUS
    else:
        classification = ContactSubmissionClass.CLEAN
    return ContactSpamVerdict(classification=classification, score=score, reasons=tuple(reasons))
