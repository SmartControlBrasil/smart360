from __future__ import annotations

import re
from dataclasses import dataclass

from .integrations import (
    _has_ai_term,
    _is_logistics_web_context,
    is_lead_capture_intent,
    is_web_system_project_text,
    web_system_interest_summary,
)
from .models import LiviaLeadCapture, LiviaMessage
from .qualification import INVALID_GENERIC_VALUES
from .technical_summary import build_technical_service_summary, extract_technical_context, technical_corpus_from_lead

MAX_EXECUTIVE_SUMMARY_CHARS = 700
MAX_KEY_POINT_CHARS = 220
MAX_KEY_POINTS = 6
MAX_TRANSCRIPT_CHARS = 14000
MAX_TRANSCRIPT_TURNS = 80

INTERNAL_CONTENT_MARKERS = (
    "correlation_id",
    "traceback",
    "api_key",
    "api-key",
    "bearer ",
    "openai",
    "anthropic",
    "prompt interno",
    "system prompt",
    "token:",
    "access_token",
    "refresh_token",
)

CONTACT_ONLY_PATTERNS = (
    r"^[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]{1,60}$",
    r"^[+()\d .-]{8,20}$",
    r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$",
)


@dataclass(frozen=True)
class ConversationSummarySections:
    executive_summary: str
    main_need: str
    key_points: tuple[str, ...]
    suggested_classification: str
    recommended_next_action: str


def _normalize(text: str) -> str:
    return str(text or "").strip().lower()


def _is_internal_message(message) -> bool:
    if message.role == LiviaMessage.Role.SYSTEM:
        return True
    content = _normalize(message.content)
    metadata = message.metadata or {}
    if metadata.get("internal") or metadata.get("debug"):
        return True
    return any(marker in content for marker in INTERNAL_CONTENT_MARKERS)


def _sanitize_transcript_line(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "").strip())
    if not cleaned:
        return ""
    if any(marker in cleaned.lower() for marker in INTERNAL_CONTENT_MARKERS):
        return ""
    if re.fullmatch(r"[A-Za-z0-9+/=]{80,}", cleaned):
        return ""
    return cleaned[:1200]


def _conversation_messages(conversation, lead=None):
    queryset = conversation.messages.exclude(role=LiviaMessage.Role.SYSTEM).order_by("created_at", "id")
    messages = list(queryset)
    if lead is not None:
        start_id = (lead.crm_reference or {}).get("capture_start_message_id")
        if start_id:
            messages = [message for message in messages if message.id >= start_id]
    return [message for message in messages if not _is_internal_message(message)]


def _is_contact_only_message(text: str) -> bool:
    value = str(text or "").strip()
    if not value:
        return True
    normalized = _normalize(value)
    if normalized in INVALID_GENERIC_VALUES:
        return True
    if is_lead_capture_intent(normalized) or is_web_system_project_text(normalized):
        return False
    if any(
        term in normalized
        for term in (
            "orcamento",
            "orçamento",
            "diagnostico",
            "diagnóstico",
            "pmoc",
            "manutencao",
            "manutenção",
            "falha",
            "problema",
            "entregas",
            "logistica",
            "logística",
        )
    ):
        return False
    return any(re.fullmatch(pattern, value, re.IGNORECASE) for pattern in CONTACT_ONLY_PATTERNS)


def _is_substantive_user_message(text: str) -> bool:
    value = str(text or "").strip()
    if not value or _is_contact_only_message(value):
        return False
    normalized = _normalize(value)
    if is_lead_capture_intent(normalized) or is_web_system_project_text(normalized):
        return True
    if len(normalized) < 8 and normalized in {"obrigado", "obrigada", "valeu", "ok", "certo", "entendi"}:
        return False
    return True


def _user_messages_for_summary(conversation, lead=None):
    return [
        message.content.strip()
        for message in _conversation_messages(conversation, lead=lead)
        if message.role == LiviaMessage.Role.USER and _is_substantive_user_message(message.content)
    ]


def _corpus_from_conversation(conversation, lead=None):
    if lead is not None:
        lead_corpus = technical_corpus_from_lead(lead)
        if lead_corpus.strip():
            return lead_corpus
    return " ".join(_user_messages_for_summary(conversation, lead=lead))


def _build_main_need(lead, corpus: str) -> str:
    normalized = _normalize(corpus)
    web_summary = web_system_interest_summary(normalized)
    if web_summary:
        return web_summary
    if lead and (lead.service_interest or "").strip():
        return str(lead.service_interest).strip()
    if lead and (lead.notes or "").strip():
        return str(lead.notes).strip()[:500]
    substantive = _user_messages_for_summary(lead.conversation, lead=lead) if lead else []
    if substantive:
        return substantive[0][:500]
    return "Necessidade ainda em detalhamento com o cliente."


def _build_executive_summary(lead, corpus: str, user_messages: list[str]) -> str:
    normalized = _normalize(corpus)
    if lead and (lead.notes or "").strip() and len(lead.notes.strip()) >= 12:
        summary = lead.notes.strip()
    elif web_system_interest_summary(normalized):
        summary = web_system_interest_summary(normalized)
    else:
        technical_summary = build_technical_service_summary(
            raw_corpus=corpus,
            city=(lead.city or "").strip() if lead else "",
        )
        summary = technical_summary or ""

    if not summary and user_messages:
        if len(user_messages) == 1:
            summary = user_messages[0]
        else:
            summary = (
                f"Conversa com {len(user_messages)} mensagens relevantes do cliente. "
                f"Contexto inicial: {user_messages[0]}"
            )
            if len(user_messages) > 1:
                summary += f" Último ponto: {user_messages[-1]}"

    if not summary:
        summary = "Lead qualificado após conversa com a Lívia."

    return summary[:MAX_EXECUTIVE_SUMMARY_CHARS]


def _build_key_points(user_messages: list[str], lead=None) -> tuple[str, ...]:
    points: list[str] = []
    seen: set[str] = set()

    history = []
    if lead is not None:
        history = list((lead.crm_reference or {}).get("technical_history") or [])

    for candidate in [*history, *user_messages]:
        value = re.sub(r"\s+", " ", str(candidate or "").strip())
        if not value or _is_contact_only_message(value):
            continue
        normalized = _normalize(value)
        if normalized in seen:
            continue
        seen.add(normalized)
        points.append(value[:MAX_KEY_POINT_CHARS])
        if len(points) >= MAX_KEY_POINTS:
            break

    if not points and lead and (lead.notes or "").strip():
        points.append(str(lead.notes).strip()[:MAX_KEY_POINT_CHARS])

    return tuple(points)


def _suggested_classification(lead, corpus: str) -> str:
    normalized = _normalize(corpus)
    urgency = lead.get_urgency_display() if lead else "Média"
    reference = (lead.crm_reference or {}) if lead else {}
    technical_context = reference.get("technical_context") or {}

    if reference.get("category") == "sistemas_web_ia" or is_web_system_project_text(normalized):
        label = "Desenvolvimento de sistema web"
        if _is_logistics_web_context(normalized):
            label += " logístico"
        if _has_ai_term(normalized) and is_web_system_project_text(normalized):
            label += " com IA integrada"
        return f"{label} | Urgência: {urgency}"

    equipment = technical_context.get("equipment") or ""
    if equipment:
        intent = technical_context.get("intent") or "atendimento técnico"
        return f"Atendimento técnico ({equipment}) — {intent} | Urgência: {urgency}"

    context = extract_technical_context(corpus)
    if context.equipment:
        return f"Atendimento técnico ({context.equipment}) | Urgência: {urgency}"

    service_interest = (lead.service_interest or "").strip() if lead else ""
    if service_interest and "consultoria" not in _normalize(service_interest):
        return f"{service_interest} | Urgência: {urgency}"

    if is_lead_capture_intent(normalized) or any(term in normalized for term in ("orcamento", "orçamento")):
        return f"Oportunidade comercial qualificada | Urgência: {urgency}"

    return f"Lead comercial qualificado | Urgência: {urgency}"


def _recommended_next_action(lead, corpus: str) -> str:
    normalized = _normalize(corpus)
    technical_context = (lead.crm_reference or {}).get("technical_context") or {} if lead else {}

    if lead and lead.urgency == LiviaLeadCapture.Urgency.EMERGENCY:
        return "Contato imediato por telefone/WhatsApp para triagem de urgência operacional."

    if technical_context.get("stopped") or technical_context.get("symptom") in {"parada", "erro low pressure"}:
        return "Confirmar criticidade da parada, alinhar diagnóstico técnico e avaliar visita ou suporte remoto."

    if _is_logistics_web_context(normalized) or (
        is_web_system_project_text(normalized) and is_lead_capture_intent(normalized)
    ):
        return (
            "Agendar conversa comercial para detalhar escopo funcional, integrações, "
            "cronograma e expectativa de investimento."
        )

    if any(term in normalized for term in ("visita tecnica", "visita técnica", "avaliacao", "avaliação")):
        return "Confirmar disponibilidade para avaliação técnica presencial ou remota."

    if any(term in normalized for term in ("orcamento", "orçamento", "cotacao", "cotação")):
        return "Retornar contato para alinhar escopo e preparar proposta comercial."

    return "Retornar contato para dar continuidade ao atendimento com base no histórico abaixo."


def build_conversation_summary(conversation, lead=None) -> ConversationSummarySections:
    user_messages = _user_messages_for_summary(conversation, lead=lead)
    corpus = _corpus_from_conversation(conversation, lead=lead)
    return ConversationSummarySections(
        executive_summary=_build_executive_summary(lead, corpus, user_messages),
        main_need=_build_main_need(lead, corpus),
        key_points=_build_key_points(user_messages, lead=lead),
        suggested_classification=_suggested_classification(lead, corpus),
        recommended_next_action=_recommended_next_action(lead, corpus),
    )


def build_conversation_transcript(conversation, lead=None) -> str:
    messages = _conversation_messages(conversation, lead=lead)
    if not messages:
        return "Sem histórico registrado nesta conversa."

    lines: list[str] = []
    total_chars = 0
    selected_messages = messages[-MAX_TRANSCRIPT_TURNS:] if len(messages) > MAX_TRANSCRIPT_TURNS else messages
    omitted_count = len(messages) - len(selected_messages)

    if omitted_count > 0:
        lines.append(f"... ({omitted_count} mensagens anteriores omitidas para legibilidade) ...")
        lines.append("")

    for message in selected_messages:
        content = _sanitize_transcript_line(message.content)
        if not content:
            continue
        speaker = "Cliente" if message.role == LiviaMessage.Role.USER else "Lívia"
        line = f"{speaker}: {content}"
        if total_chars + len(line) > MAX_TRANSCRIPT_CHARS:
            lines.append("... (histórico truncado para caber no e-mail) ...")
            break
        lines.append(line)
        total_chars += len(line)

    return "\n".join(lines) if lines else "Sem histórico registrado nesta conversa."


def format_conversation_summary_sections(summary: ConversationSummarySections) -> str:
    lines = [
        "Resumo executivo:",
        summary.executive_summary,
        "",
        "Necessidade principal:",
        summary.main_need,
        "",
        "Pontos importantes levantados:",
    ]
    if summary.key_points:
        lines.extend(f"- {point}" for point in summary.key_points)
    else:
        lines.append("- Não identificado em mensagens detalhadas do cliente.")

    lines.extend(
        [
            "",
            "Classificação sugerida:",
            summary.suggested_classification,
            "",
            "Próxima ação recomendada:",
            summary.recommended_next_action,
        ]
    )
    return "\n".join(lines)


def build_lead_notification_body(livia_lead, *, timestamp: str) -> str:
    conversation = livia_lead.conversation
    summary = build_conversation_summary(conversation, lead=livia_lead)
    transcript = build_conversation_transcript(conversation, lead=livia_lead)
    origin = (conversation.source_page or "livia_assistant").strip() or "livia_assistant"

    return "\n".join(
        [
            "Novo lead qualificado pela Lívia",
            "",
            f"Nome: {livia_lead.name or 'Não informado'}",
            f"Empresa: {livia_lead.company or 'Não informado'}",
            f"Cidade: {livia_lead.city or 'Não informada'}",
            f"Telefone/WhatsApp: {livia_lead.phone or 'Não informado'}",
            f"E-mail: {livia_lead.email or 'Não informado'}",
            f"Interesse/problema: {livia_lead.notes or 'Não informado'}",
            f"Origem: {origin}",
            f"Data/hora: {timestamp}",
            "",
            format_conversation_summary_sections(summary),
            "",
            "Histórico da conversa:",
            transcript,
        ]
    )
