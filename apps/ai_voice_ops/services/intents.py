from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedIntent:
    key: str
    confidence: float
    entities: dict
    is_action: bool
    persona: str


class VoiceIntentService:
    PERSONA_INTENTS = {
        "technician": {
            "start_work_order": ["iniciar ordem", "iniciar os", "comecar os", "iniciar atendimento"],
            "complete_work_order": ["finalizar os", "concluir os", "encerrar os", "finalizar ordem"],
            "report_issue": ["registrar problema", "ativo esta com", "equipamento esta com", "reportar problema", "abrir observacao"],
            "add_part": ["adicionar peca", "usar peca", "lancar material", "incluir peca"],
            "mark_checklist_nok": ["checklist item nok", "marcar item nok", "item nok", "checklist nok"],
            "request_help": ["preciso de ajuda", "me ajude", "orientacao tecnica", "ajuda com esse equipamento"],
            "query_status": ["qual o status", "status da os", "como esta a ordem"],
            "query_schedule": ["qual minha agenda", "proxima visita", "agenda de hoje", "roteiro de hoje"],
            "query_risk": ["qual o risco", "ativo em risco", "por que esta em atencao"],
        },
        "manager": {
            "query_summary": ["resuma a operacao", "resuma a operacao", "o que esta critico hoje", "resuma a situacao"],
            "query_status": ["tem decisao pendente", "qual backlog atual", "quais unidades estao em risco", "status da operacao"],
            "query_schedule": ["como esta a agenda", "tecnicos sobrecarregados", "agenda critica"],
            "query_risk": ["maior risco", "anomalias", "unidades em risco", "onde esta o gargalo"],
        },
        "client": {
            "query_status": ["qual status do meu chamado", "status da minha os", "como esta meu atendimento", "tem orcamento pendente"],
            "query_schedule": ["tem visita agendada", "quando sera a manutencao", "agenda da visita"],
            "query_summary": ["resuma minha unidade", "como esta minha operacao", "o que esta pendente"],
            "query_risk": ["tem algo em risco", "por que esse ativo esta em atencao"],
        },
    }

    ORDER_PATTERN = re.compile(r"\b(?:OS|SO)-?\d{2,4}-?\d+\b", re.IGNORECASE)
    PART_PATTERN = re.compile(r"\b(?:PRT|PART)-?\d+\b", re.IGNORECASE)
    ASSET_PATTERN = re.compile(r"\b(?:AST|CHILLER|EQP|ATIVO)-?[A-Z0-9\-]+\b", re.IGNORECASE)

    @classmethod
    def parse(cls, *, persona: str, transcript_text: str) -> ParsedIntent:
        normalized = (transcript_text or "").strip().lower()
        catalog = cls.PERSONA_INTENTS.get(persona, {})
        best_key = "query_summary" if persona != "technician" else "request_help"
        best_confidence = 0.35
        for intent, keywords in catalog.items():
            matches = sum(1 for keyword in keywords if keyword in normalized)
            if not matches:
                continue
            confidence = min(0.55 + (matches * 0.18), 0.98)
            if confidence > best_confidence:
                best_key = intent
                best_confidence = confidence
        entities = cls._extract_entities(transcript_text)
        is_action = best_key in {
            "start_work_order",
            "complete_work_order",
            "report_issue",
            "add_part",
            "mark_checklist_nok",
            "request_help",
        }
        return ParsedIntent(
            key=best_key,
            confidence=round(best_confidence, 2),
            entities=entities,
            is_action=is_action,
            persona=persona,
        )

    @classmethod
    def _extract_entities(cls, transcript_text: str) -> dict:
        transcript_text = transcript_text or ""
        order_match = cls.ORDER_PATTERN.search(transcript_text)
        part_match = cls.PART_PATTERN.search(transcript_text)
        asset_match = cls.ASSET_PATTERN.search(transcript_text)
        quantity_match = re.search(r"\b(\d+(?:[\,\.]\d+)?)\s*(?:un|peca|pecas|item|itens)?\b", transcript_text, flags=re.IGNORECASE)
        issue_match = re.search(r"(?:problema|ruido|falha|com)\s+(.+)$", transcript_text, flags=re.IGNORECASE)
        return {
            "order_code": order_match.group(0).replace(" ", "") if order_match else "",
            "part_code": part_match.group(0).replace(" ", "") if part_match else "",
            "asset_code": asset_match.group(0).replace(" ", "") if asset_match else "",
            "quantity": quantity_match.group(1).replace(",", ".") if quantity_match else "",
            "issue_summary": issue_match.group(1).strip(" .") if issue_match else "",
        }

    @classmethod
    def supported_intents(cls, persona: str) -> list[str]:
        return sorted(cls.PERSONA_INTENTS.get(persona, {}).keys())

