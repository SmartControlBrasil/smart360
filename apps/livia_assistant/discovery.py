from __future__ import annotations

import re
import unicodedata

MIN_DISCOVERY_ANSWERS = 2
MIN_GENERIC_DIGITAL_DISCOVERY_ANSWERS = 4
MIN_FOOD_DELIVERY_FUNCTIONAL_AREAS = 4

DIGITAL_PRODUCT_MARKERS = (
    "aplicativo",
    "app mobile",
    " mobile",
    "moveis",
    "móveis",
    "plataforma",
    "saas",
    "delivery",
    "cardapio",
    "cardápio",
    "tablet",
    "portal",
    "e-commerce",
    "ecommerce",
    "sistema web",
    "sistema de entrega",
    "app de",
    "software sob medida",
)

FOOD_DELIVERY_FUNCTIONAL_CHECKS = {
    "order_channel": (
        "app",
        "site",
        "tablet",
        "whatsapp",
        "telefone",
        "balcao",
        "balcão",
        "celular",
        "web",
    ),
    "delivery_model": (
        "entregador",
        "motoboy",
        "terceiro",
        "terceiriz",
        "proprio",
        "próprio",
        "proprios",
        "próprios",
        "parceiro",
        "ifood",
        "rappi",
    ),
    "payment": (
        "pagamento",
        "pix",
        "cartao",
        "cartão",
        "online",
        "credito",
        "crédito",
        "debito",
        "débito",
    ),
    "scale": (
        "unidade",
        "loja",
        "lojas",
        "rede",
        "franquia",
        "estabelecimento",
        "pizzaria",
        "pizzarias",
        "restaurante",
    ),
    "admin_features": (
        "painel",
        "administrativo",
        "cardapio",
        "cardápio",
        "produtos",
        "status do pedido",
        "status dos pedidos",
    ),
}

FOOD_DELIVERY_DISCOVERY_QUESTIONS = {
    "business_model": (
        "Para entrega de alimentos, normalmente o sistema precisa controlar pedidos, clientes, entregadores, "
        "status da entrega, taxas e painel administrativo. Hoje você quer algo para uso interno do seu negócio "
        "ou uma plataforma para vários estabelecimentos?"
    ),
    "order_channel": (
        "O pedido será feito por app, site, tablet interno na loja ou uma combinação desses canais?"
    ),
    "delivery_model": (
        "A entrega será feita por entregadores próprios, terceiros ou ambos?"
    ),
    "payment": (
        "Você precisa de pagamento online integrado ou só controle operacional dos pedidos?"
    ),
    "scale": (
        "Quantas unidades ou lojas entram nessa primeira fase?"
    ),
    "admin_features": (
        "Você precisa de painel administrativo com cardápio, produtos e status dos pedidos em tempo real?"
    ),
}

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


def is_digital_product_context(normalized_text: str, messages) -> bool:
    corpus = _normalize(_conversation_text(messages, normalized_text))
    if any(marker in corpus for marker in DIGITAL_PRODUCT_MARKERS):
        return True
    if _is_food_delivery_context(normalized_text, messages):
        return True
    helpers = _integration_helpers()
    if helpers["is_web_system_project_text"](corpus):
        return True
    if _is_mobile_app_context(normalized_text, messages):
        return True
    return False


def _is_mobile_app_context(normalized_text: str, messages) -> bool:
    corpus = _normalize(_conversation_text(messages, normalized_text))
    return any(
        term in corpus
        for term in (
            "aplicativo",
            "aplicativos",
            "app mobile",
            "mobile",
            "moveis",
            "móveis",
        )
    )


def _has_discovery_dimension(corpus: str, dimension: str) -> bool:
    if dimension == "system_type":
        return any(
            term in corpus
            for term in ("sistema", "app", "aplicativo", "plataforma", "software", "delivery", "portal")
        )
    if dimension == "business_context":
        return any(
            term in corpus
            for term in (
                "pizzaria",
                "pizzarias",
                "restaurante",
                "lanchonete",
                "empresa",
                "rede",
                "loja",
                "lojas",
                "negocio",
                "negócio",
                "franquia",
                "estabelecimento",
            )
        )
    if dimension == "primary_objective":
        return any(
            term in corpus
            for term in (
                "entrega",
                "cardapio",
                "cardápio",
                "automatiz",
                "pedido",
                "pedidos",
                "vendas",
                "gestao",
                "gestão",
                "operacao",
                "operação",
                "tablet",
            )
        )
    return False


def _food_delivery_functional_coverage(corpus: str) -> dict[str, bool]:
    return {
        area: any(term in corpus for term in terms)
        for area, terms in FOOD_DELIVERY_FUNCTIONAL_CHECKS.items()
    }


def _count_food_delivery_functional_areas(corpus: str) -> int:
    return sum(1 for covered in _food_delivery_functional_coverage(corpus).values() if covered)


def _has_rich_digital_business_context(corpus: str) -> bool:
    rich_markers = (
        "rede de",
        "pequena rede",
        "franquia",
        "varias lojas",
        "várias lojas",
        "entrega automatizada",
        "cardapio no tablet",
        "cardápio no tablet",
    )
    business_markers = ("pizzaria", "pizzarias", "restaurante", "lanchonete", "hamburgueria", "padaria")
    has_business = any(marker in corpus for marker in business_markers)
    has_rich = any(marker in corpus for marker in rich_markers)
    return has_business and has_rich


def _pick_food_delivery_discovery_question(corpus: str) -> str:
    coverage = _food_delivery_functional_coverage(corpus)
    priority = ("delivery_model", "payment", "scale", "admin_features", "order_channel", "business_model")
    for area in priority:
        if area == "business_model" and coverage.get("scale"):
            continue
        if not coverage.get(area, False):
            return FOOD_DELIVERY_DISCOVERY_QUESTIONS[area]
    return FOOD_DELIVERY_DISCOVERY_QUESTIONS["delivery_model"]


def has_minimum_digital_product_discovery(messages, normalized_text: str = "") -> bool:
    corpus = _normalize(_conversation_text(messages, normalized_text))
    if not is_digital_product_context(normalized_text, messages):
        return count_substantive_discovery_answers(messages) >= MIN_DISCOVERY_ANSWERS

    required_dimensions = ("system_type", "business_context", "primary_objective")
    if not all(_has_discovery_dimension(corpus, dimension) for dimension in required_dimensions):
        return False

    if _is_food_delivery_context(normalized_text, messages):
        coverage = _food_delivery_functional_coverage(corpus)
        mandatory_areas = ("delivery_model", "payment", "scale", "admin_features")
        if not all(coverage.get(area) for area in mandatory_areas):
            return False
        return _count_food_delivery_functional_areas(corpus) >= MIN_FOOD_DELIVERY_FUNCTIONAL_AREAS

    if _is_mobile_app_context(normalized_text, messages):
        return count_substantive_discovery_answers(messages) >= MIN_GENERIC_DIGITAL_DISCOVERY_ANSWERS

    helpers = _integration_helpers()
    if helpers["is_web_system_project_text"](corpus) or helpers["_is_logistics_web_context"](corpus):
        return count_substantive_discovery_answers(messages) >= MIN_GENERIC_DIGITAL_DISCOVERY_ANSWERS

    return count_substantive_discovery_answers(messages) >= MIN_GENERIC_DIGITAL_DISCOVERY_ANSWERS


def build_digital_product_interest_summary(normalized_text: str) -> str:
    corpus = _normalize(normalized_text)
    if not is_digital_product_context(corpus, [{"role": "user", "content": corpus}]):
        return ""

    if _is_food_delivery_context(corpus, [{"role": "user", "content": corpus}]):
        features: list[str] = []
        if any(term in corpus for term in ("entrega", "delivery", "delivery de comida")):
            features.append("delivery de comida")
        if any(term in corpus for term in ("cardapio", "cardápio", "tablet")):
            features.append("cardápio em tablet")
        if any(term in corpus for term in ("app", "aplicativo", "mobile", "moveis", "móveis")):
            features.append("aplicativo")

        business = "o negócio"
        if "rede de pizzarias" in corpus or ("rede" in corpus and "pizzaria" in corpus):
            business = "uma pequena rede de pizzarias"
        elif "pizzaria" in corpus or "pizzarias" in corpus:
            business = "pizzaria"
        elif "restaurante" in corpus:
            business = "restaurante"

        feature_text = " e ".join(features) if features else "operação digital"
        return f"sistema/app para {feature_text} para {business}"

    if _is_mobile_app_context(corpus, [{"role": "user", "content": corpus}]):
        return "desenvolvimento de aplicativo mobile sob medida"

    return ""


def discovery_minimum_met(messages, normalized_text: str = "") -> bool:
    if not normalized_text:
        for message in reversed(messages or []):
            if message.get("role") == "user":
                normalized_text = _normalize(message.get("content") or "")
                break
    return has_minimum_digital_product_discovery(messages, normalized_text)


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
    return not discovery_minimum_met(messages, normalized_text)


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
            "delivery de comida",
            "sistema de entrega",
            "entregadores",
            "restaurante",
            "lanchonete",
            "pizzaria",
            "pizzarias",
            "ifood",
            "cardapio",
            "cardápio",
        )
    )


def _food_delivery_discovery_questions() -> tuple[str, ...]:
    return tuple(FOOD_DELIVERY_DISCOVERY_QUESTIONS.values())


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
    corpus = _normalize(_conversation_text(messages, normalized))
    answer_count = count_substantive_discovery_answers(messages)
    is_food_delivery = _is_food_delivery_context(normalized, messages)
    is_mobile_app = _is_mobile_app_context(normalized, messages)

    if is_food_delivery:
        question = _pick_food_delivery_discovery_question(corpus)
        if _has_rich_digital_business_context(corpus):
            return f"Ótimo, isso já ajuda bastante a entender a operação. {question}"
        if answer_count == 0:
            return question
        acknowledgements = (
            "Perfeito, isso ajuda bastante. ",
            "Ótimo, estou entendendo melhor a operação. ",
            "Certo, com esse contexto já consigo avançar. ",
        )
        ack = acknowledgements[min(answer_count - 1, len(acknowledgements) - 1)]
        return f"{ack}{question}"

    if is_mobile_app and answer_count == 0:
        return (
            "Sim, desenvolvemos aplicativos mobile e sistemas web integrados sob medida. "
            "Qual seria a finalidade principal do app: vendas, entregas, atendimento, operação interna ou outro processo?"
        )

    if _is_warehouse_context(normalized, messages):
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
    digital_summary = build_digital_product_interest_summary(corpus)
    if digital_summary:
        return (
            f"Entendi. Temos um bom ponto de partida para {digital_summary}. "
            "Para nossa equipe avaliar melhor, posso registrar seu atendimento? "
        )
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
