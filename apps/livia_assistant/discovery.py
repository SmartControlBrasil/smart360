from __future__ import annotations

import re
import unicodedata

MIN_DISCOVERY_ANSWERS = 2

EXPLICIT_FORWARDING_TERMS = (
    "quero orcamento",
    "quero orçamento",
    "preciso de orcamento",
    "preciso de orçamento",
    "mande uma proposta",
    "manda uma proposta",
    "quero proposta",
    "preciso de proposta",
    "pode me ligar",
    "me liga",
    "quero falar com um especialista",
    "quero falar com especialista",
    "falar com especialista",
    "falar com um especialista",
    "quero contratar",
    "preciso contratar",
    "quero comprar",
    "preciso de atendimento",
    "quero atendimento",
    "pode encaminhar",
    "encaminhar meu pedido",
    "contato humano",
    "chama no whatsapp",
    "chama no zap",
    "quero um diagnostico",
    "quero um diagnóstico",
    "preciso de diagnostico",
    "preciso de diagnóstico",
    "preciso de manutencao",
    "preciso de manutenção",
    "preciso de suporte",
    "suporte tecnico",
    "suporte técnico",
    "visita tecnica",
    "visita técnica",
    "agendar visita",
    "minha maquina esta parada",
    "minha máquina está parada",
    "linha parada",
)

CONSULTATIVE_SOLUTION_TERMS = (
    "sistema",
    "software",
    "plataforma",
    " aplicativo",
    " app ",
    "portal",
    "automação",
    "automacao",
    "integração",
    "integracao",
    "supervisório",
    "supervisorio",
    "deposito",
    "depósito",
    "estoque",
    "armazem",
    "armazém",
    "crm",
    "dashboard",
    "planilha",
    "desenvolver",
    "desenvolvimento",
    "retrofit",
    "saas",
    "erp",
    "logistica",
    "logística",
)


def _normalize(text: str) -> str:
    normalized = (text or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", normalized)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _conversation_text(messages, current_normalized="") -> str:
    parts = [str(message.get("content") or "") for message in messages or [] if message.get("role") == "user"]
    if current_normalized:
        parts.append(current_normalized)
    return " ".join(parts)


def _integration_helpers():
    from .integrations import (
        _is_followup_lead_collection,
        _is_logistics_web_context,
        is_clear_technical_issue,
        is_lead_capture_intent,
        is_lead_data_message,
        is_web_system_project_text,
    )

    return {
        "is_clear_technical_issue": is_clear_technical_issue,
        "is_lead_capture_intent": is_lead_capture_intent,
        "is_lead_data_message": is_lead_data_message,
        "is_web_system_project_text": is_web_system_project_text,
        "_is_logistics_web_context": _is_logistics_web_context,
        "_is_followup_lead_collection": _is_followup_lead_collection,
    }


def is_explicit_forwarding_intent(normalized_text: str) -> bool:
    normalized = _normalize(normalized_text)
    if not normalized:
        return False
    if any(term in normalized for term in EXPLICIT_FORWARDING_TERMS):
        return True
    return _integration_helpers()["is_lead_capture_intent"](normalized)


def is_consultative_solution_topic(normalized_text: str) -> bool:
    normalized = _normalize(normalized_text)
    if not normalized:
        return False
    if is_explicit_forwarding_intent(normalized):
        return False
    maintenance_service_markers = (
        "consertar",
        "conserto",
        "manutencao",
        "manutenção",
        "cuidar dos meus equipamentos",
        "cuidar dos equipamentos",
        "empresa de automacao para cuidar",
        "empresa de automação para cuidar",
        "equipamento que parou",
        "equipamennto que parou",
        "camara frigorifica",
        "câmara frigorífica",
        "ar condicionado",
        "inversor",
        "falha",
        "parou",
        "nao gela",
        "não gela",
    )
    if any(marker in normalized for marker in maintenance_service_markers):
        return False
    return any(term in normalized for term in CONSULTATIVE_SOLUTION_TERMS)


def conversation_has_open_solution_need(messages) -> bool:
    for message in messages or []:
        if message.get("role") != "user":
            continue
        normalized = _normalize(message.get("content") or "")
        if is_consultative_solution_topic(normalized):
            return True
    return False


def _is_substantive_discovery_answer(content: str) -> bool:
    helpers = _integration_helpers()
    value = str(content or "").strip()
    normalized = _normalize(value)
    if len(normalized) < 6:
        return False
    if normalized in {"ok", "sim", "nao", "não", "obrigado", "obrigada", "valeu", "certo", "entendi"}:
        return False
    if helpers["is_lead_data_message"](value):
        return False
    if re.fullmatch(r"[+()\d .-]{8,20}", value):
        return False
    return True


def count_substantive_discovery_answers(messages) -> int:
    started = False
    count = 0
    for message in messages or []:
        if message.get("role") != "user":
            continue
        content = str(message.get("content") or "")
        normalized = _normalize(content)
        if not started:
            if is_consultative_solution_topic(normalized):
                started = True
            continue
        if _is_substantive_discovery_answer(content):
            count += 1
    return count


def discovery_minimum_met(messages) -> bool:
    return count_substantive_discovery_answers(messages) >= MIN_DISCOVERY_ANSWERS


def needs_consultative_discovery(
    messages,
    normalized_text: str,
    *,
    qualified_cycle_locked: bool = False,
    ignore_explicit_forwarding: bool = False,
) -> bool:
    del qualified_cycle_locked
    helpers = _integration_helpers()
    if helpers["_is_followup_lead_collection"](messages):
        return False
    if helpers["is_clear_technical_issue"](normalized_text):
        return False
    if not ignore_explicit_forwarding and is_explicit_forwarding_intent(normalized_text):
        return False
    if not conversation_has_open_solution_need(messages):
        return False
    return not discovery_minimum_met(messages)


def _is_warehouse_context(normalized_text: str, messages) -> bool:
    corpus = _normalize(_conversation_text(messages, normalized_text))
    return any(
        term in corpus
        for term in (
            "deposito",
            "depósito",
            "estoque",
            "armazem",
            "armazém",
            "materiais de construcao",
            "materiais de construção",
            "almoxarifado",
        )
    )


def _is_food_delivery_context(normalized_text: str, messages) -> bool:
    corpus = _normalize(_conversation_text(messages, normalized_text))
    return any(
        term in corpus
        for term in (
            "entrega de alimentos",
            "entrega de comida",
            "delivery de alimentos",
            "entregadores",
            "restaurante",
            "lanchonete",
            "ifood",
            "cardapio",
            "cardápio",
        )
    )


def _food_delivery_discovery_questions() -> tuple[str, ...]:
    return (
        "Para entrega de alimentos, normalmente o sistema precisa controlar pedidos, clientes, entregadores, status da entrega, taxas e painel administrativo. Hoje você quer algo para uso interno do seu negócio ou uma plataforma para vários estabelecimentos?",
        "Hoje os pedidos chegam por WhatsApp, telefone, app próprio ou de forma manual?",
        "Você precisa acompanhar entregadores em tempo real e calcular taxa por bairro ou distância?",
        "O acesso precisa ser pelo celular, computador ou ambos?",
    )


def _warehouse_discovery_questions() -> tuple[str, ...]:
    return (
        "Hoje sua maior dor é controlar estoque, organizar pedidos/entregas ou acompanhar o movimento geral do depósito?",
        "Vocês controlam isso em planilha, papel, sistema pronto ou ainda não têm controle estruturado?",
        "Quantas pessoas usariam esse sistema no dia a dia?",
        "Você precisa acessar pelo celular, computador ou ambos?",
    )


def _web_system_discovery_questions() -> tuple[str, ...]:
    return (
        "Para direcionar melhor, qual processo você quer resolver primeiro com esse sistema?",
        "Hoje vocês controlam isso em planilha, sistema pronto ou ainda de forma manual?",
        "Quantas pessoas usariam a solução no dia a dia?",
        "O acesso precisa ser pelo celular, computador ou ambos?",
    )


def _generic_solution_discovery_questions() -> tuple[str, ...]:
    return (
        "Que tipo de sistema você precisa: controle interno, estoque, vendas, entregas, atendimento ou outro processo?",
        "Como vocês fazem esse controle hoje: planilha, sistema pronto, processo manual ou ainda sem padronização?",
        "Qual parte da operação mais precisa de ganho imediato?",
        "Existe prazo ou urgência para colocar isso em uso?",
    )


def build_consultative_discovery_reply(normalized_text: str, messages) -> str:
    helpers = _integration_helpers()
    normalized = _normalize(normalized_text)
    answer_count = count_substantive_discovery_answers(messages)
    is_food_delivery = _is_food_delivery_context(normalized, messages)

    if is_food_delivery:
        questions = _food_delivery_discovery_questions()
        intro = "Entendi. "
    elif _is_warehouse_context(normalized, messages):
        questions = _warehouse_discovery_questions()
        intro = (
            "Entendi. Um sistema para o depósito pode organizar estoque, movimentações e operação com muito mais controle. "
        )
    elif helpers["is_web_system_project_text"](normalized) or helpers["_is_logistics_web_context"](normalized):
        questions = _web_system_discovery_questions()
        intro = "Perfeito. Dá para estruturar isso como um sistema web sob medida para a operação. "
    else:
        questions = _generic_solution_discovery_questions()
        intro = "Claro. "

    question_index = min(answer_count, len(questions) - 1)
    if answer_count == 0:
        if is_food_delivery:
            return questions[0]
        return f"{intro}{questions[0]}"
    acknowledgements = (
        "Perfeito, isso ajuda bastante. ",
        "Ótimo, estou entendendo melhor a operação. ",
        "Certo, com esse contexto já consigo avançar. ",
    )
    ack = acknowledgements[min(answer_count - 1, len(acknowledgements) - 1)]
    return f"{ack}{questions[question_index]}"


def build_discovery_to_collection_handoff(normalized_text: str, messages) -> str:
    helpers = _integration_helpers()
    normalized = _normalize(normalized_text)
    corpus = _normalize(_conversation_text(messages, normalized))
    if _is_warehouse_context(normalized, messages):
        return (
            "Entendi. Isso já dá para desenhar como um sistema web sob medida para gestão do depósito. "
            "Para nossa equipe avaliar melhor, posso registrar seu atendimento. "
        )
    if helpers["is_web_system_project_text"](corpus) or helpers["_is_logistics_web_context"](corpus):
        return (
            "Entendi. Isso já dá para estruturar como um sistema web sob medida para a operação. "
            "Para nossa equipe avaliar melhor, posso registrar seu atendimento. "
        )
    return (
        "Entendi. Com o cenário que você descreveu, já consigo encaminhar uma análise mais precisa. "
        "Para registrar seu atendimento, "
    )
