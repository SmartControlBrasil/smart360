from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def normalize_technical_corpus(text: str) -> str:
    """Normaliza termos técnicos comuns para detecção e resumo."""
    normalized = _normalize(text)
    replacements = (
        ("equipamennto", "equipamento"),
        ("camara frigorifica", "câmara frigorífica"),
        ("camara climatica", "câmara climática"),
        ("choque termico", "choque térmico"),
        ("nao gela", "não gela"),
        ("acumulo de gelo", "acúmulo de gelo"),
        ("painel eletrico", "painel elétrico"),
        ("placa eletronica", "placa eletrônica"),
        ("maquina industrial", "máquina industrial"),
        ("maquina parada", "máquina parada"),
        ("equipamento parado", "equipamento parado"),
        ("disjuntor caindo", "disjuntor desarmando"),
        ("disjuntor cai", "disjuntor desarmando"),
        ("possivel contrato", "possível contrato"),
        ("avaliacao", "avaliação"),
        ("visita tecnica", "visita técnica"),
        ("atendimento tecnico", "atendimento técnico"),
        ("baixa pressao", "baixa pressão"),
        ("falha eletrica", "falha elétrica"),
        ("compressor nao liga", "compressor não liga"),
        ("robo de limpeza", "robô de limpeza"),
        ("robo de seguranca", "robô de segurança"),
        ("servo motor", "servo motor"),
    )
    for source, target in replacements:
        normalized = normalized.replace(source, target)
    return normalized


@dataclass(frozen=True)
class TechnicalContext:
    equipment: str = ""
    brand: str = ""
    symptom: str = ""
    intent: str = ""
    stopped: bool = False


def _detect_brand(corpus: str) -> str:
    if "weiss" in corpus:
        return "Weiss"
    if any(term in corpus for term in ("votsch", "vötsch")):
        return "Vötsch"
    return ""


def detect_equipment(corpus: str) -> tuple[str, str]:
    normalized = normalize_technical_corpus(corpus)
    brand = _detect_brand(normalized)

    equipment_rules = (
        ("câmara frigorífica", ("câmara frigorífica",)),
        ("câmara climática", ("câmara climática",)),
        ("choque térmico", ("choque térmico",)),
        ("robô de limpeza", ("robô de limpeza", "duno", "dune", "hygibot")),
        ("robô de segurança", ("robô de segurança",)),
        ("servo motor", ("servo motor",)),
        ("inversor", ("inversor",)),
        ("compressor", ("compressor",)),
        ("CLP", ("clp",)),
        ("IHM", ("ihm",)),
        ("painel elétrico", ("painel elétrico",)),
        ("placa eletrônica", ("placa eletrônica",)),
        ("máquina industrial", ("máquina industrial",)),
        ("robô", ("robô", "robo")),
    )
    for label, markers in equipment_rules:
        if any(marker in normalized for marker in markers):
            if label == "câmara climática" and brand:
                return f"câmara climática {brand}", brand
            if label == "choque térmico":
                if brand:
                    return f"equipamento de choque térmico {brand}", brand
                return "equipamento de choque térmico", ""
            return label, brand

    if ("supermercado" in normalized or "limpeza" in normalized) and any(
        term in normalized for term in ("robô", "robo", "duno", "dune")
    ):
        return "robô de limpeza", brand

    return "", brand


def detect_symptom(corpus: str) -> tuple[str, bool]:
    """Retorna (sintoma normalizado, indica parada operacional)."""
    normalized = normalize_technical_corpus(corpus)

    symptom_rules = (
        ("acúmulo de gelo no ventilador", ("acúmulo de gelo", "gelo no ventilador")),
        ("disjuntor desarmando", ("disjuntor desarmando",)),
        ("erro low pressure", ("low pressure",)),
        ("não gela", ("não gela",)),
        ("painel apagado", ("painel apagou", "painel parou", "apagou o painel", "apagou o painel")),
        ("baixa pressão", ("baixa pressão",)),
        ("compressor não liga", ("compressor não liga",)),
        ("falha no ventilador", ("falha no ventilador",)),
        ("erro no painel", ("erro no painel",)),
        ("falha elétrica", ("falha elétrica",)),
        ("curto-circuito", ("curto-circuito", "curto circuito")),
        ("sobrecarga", ("sobrecarga",)),
        ("vazamento", ("vazamento",)),
        ("sensor falhando", ("sensor falhando", "sensor com falha")),
    )
    for label, markers in symptom_rules:
        if any(marker in normalized for marker in markers):
            return label, False

    stopped_markers = (
        "equipamento parado",
        "máquina parada",
        "maquina parada",
        "minha maquina parou",
        "minha máquina parou",
        "que parou",
        " parou",
    )
    if any(marker in normalized for marker in stopped_markers) or normalized.endswith("parou"):
        return "parada", True

    return "", False


def detect_intent(corpus: str) -> str:
    normalized = normalize_technical_corpus(corpus)
    has_evaluation = any(
        term in normalized
        for term in ("avaliação", "visita técnica", "diagnóstico", "diagnostico")
    )
    has_contract = any(
        term in normalized
        for term in ("possível contrato", "contrato de manutenção", "contrato de manutencao")
    )
    has_quote = any(term in normalized for term in ("orçamento", "orcamento"))
    has_service = any(
        term in normalized
        for term in ("atendimento técnico", "especialista", "pode agendar uma visita", "agendar uma visita")
    )

    if has_evaluation and has_contract:
        return "avaliação técnica e possível contrato de manutenção"
    if has_evaluation:
        return "avaliação técnica"
    if has_quote:
        return "orçamento"
    if has_contract:
        return "possível contrato de manutenção"
    if has_service:
        return "atendimento técnico"
    if any(term in normalized for term in ("diagnóstico", "diagnostico")):
        return "diagnóstico técnico"
    return "atendimento técnico"


def extract_technical_context(corpus: str) -> TechnicalContext:
    normalized = normalize_technical_corpus(corpus)
    equipment, brand = detect_equipment(normalized)
    symptom, stopped = detect_symptom(normalized)
    intent = detect_intent(normalized)
    return TechnicalContext(
        equipment=equipment,
        brand=brand,
        symptom=symptom,
        intent=intent,
        stopped=stopped,
    )


def _symptom_clause(context: TechnicalContext, corpus: str) -> str:
    normalized = normalize_technical_corpus(corpus)
    has_low_pressure = "low pressure" in normalized
    has_no_gela = "não gela" in normalized

    if context.symptom == "acúmulo de gelo no ventilador":
        return " com acúmulo de gelo no ventilador"
    if context.symptom == "disjuntor desarmando":
        return " com disjuntor desarmando"
    if context.symptom == "painel apagado":
        return " com painel apagado"
    if has_no_gela and has_low_pressure:
        return " que não gela, com erro low pressure"
    if has_no_gela:
        return " que não gela"
    if has_low_pressure:
        return ", com erro low pressure"
    if context.symptom == "parada" or context.stopped:
        return " parada"
    if context.symptom:
        return f" com {context.symptom}"
    return ""


def build_technical_service_summary(*, raw_corpus: str, city: str = "") -> str:
    corpus = normalize_technical_corpus(raw_corpus)
    if not corpus.strip():
        return ""

    context = extract_technical_context(corpus)
    city_suffix = f", em {city.strip()}" if city and city.strip() else ""
    symptom_suffix = _symptom_clause(context, corpus)

    if context.equipment:
        equipment_phrase = context.equipment
        if context.equipment == "câmara frigorífica" and symptom_suffix == " parada":
            summary = f"Solicitação de {context.intent} para câmara frigorífica parada"
        else:
            summary = f"Solicitação de {context.intent} para {equipment_phrase}{symptom_suffix}"
        return f"{summary}{city_suffix}."

    if context.symptom or context.stopped:
        symptom_text = context.symptom or "falha operacional informada"
        if symptom_text == "parada":
            symptom_text = "falha operacional informada"
        summary = f"Solicitação de {context.intent} para equipamento industrial com {symptom_text}"
        return f"{summary}{city_suffix}."

    if any(
        term in corpus
        for term in (
            "problema",
            "falha",
            "parou",
            "nao funciona",
            "não funciona",
            "defeito",
            "manutenção",
            "manutencao",
            "atendimento",
            "suporte",
        )
    ):
        summary = f"Solicitação de {context.intent} para equipamento industrial com falha operacional informada"
        return f"{summary}{city_suffix}."

    return ""


def technical_corpus_from_lead(lead) -> str:
    reference = lead.crm_reference or {}
    history = reference.get("technical_history")
    if history:
        return " ".join(str(item) for item in history if item)
    return str(lead.notes or "")
