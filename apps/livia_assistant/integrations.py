import logging
import os
import re
import unicodedata
from abc import ABC, abstractmethod
from types import SimpleNamespace

from django.conf import settings

from .discovery import (
    build_consultative_discovery_reply,
    build_discovery_to_collection_handoff,
    build_digital_product_interest_summary,
    conversation_has_open_solution_need,
    discovery_minimum_met,
    needs_consultative_discovery,
)

from .qualification import (
    _is_valid_company_or_city,
    _is_valid_email,
    _is_valid_name,
    _is_valid_phone,
    first_missing_required_field,
    strip_repetition_noise,
)

logger = logging.getLogger(__name__)


EMERGENCY_TERMS = (
    "fumaca",
    "fumaça",
    "cheiro de queimado",
    "queimado no painel",
    "curto",
    "curto-circuito",
    "choque",
    "vazamento de gas",
    "vazamento de gás",
    "incendio",
    "incêndio",
    "faisca",
    "faísca",
    "explosao",
    "explosão",
    "cabo derretendo",
    "superaquecimento critico",
    "superaquecimento crítico",
    "risco estrutural",
)

LEAD_INTENT_TERMS = (
    "orçamento",
    "orcamento",
    "cotação",
    "cotacao",
    "proposta",
    "diagnostico",
    "visita tecnica",
    "visita técnica",
    "visita",
    "contato humano",
    "falar com especialista",
    "especialista",
    "comprar",
    "contratar",
    "agendar",
    "atendimento comercial",
    "preciso de manutencao",
    "preciso de manutenção",
    "preciso de suporte",
    "suporte tecnico",
    "suporte técnico",
    "linha parada",
    "minha maquina esta parada",
    "minha máquina está parada",
    "pode me ligar",
    "chama no whatsapp",
    "chama no zap",
    "quero um diagnostico",
    "quero um diagnóstico",
    "pode encaminhar",
    "pode encaminhar meu pedido",
    "quero atendimento",
    "preciso de atendimento",
)

SERVICE_KEYWORDS = {
    "PMOC": ("pmoc",),
    "ar-condicionado": ("ar-condicionado", "ar condicionado", "climatização", "climatizacao"),
    "câmaras climáticas": ("câmara", "camara", "climática", "climatica"),
    "equipamentos de academia": ("academia", "esteira", "bike", "musculação", "musculacao"),
    "automação industrial": ("automação", "automacao", "clp", "plc", "ihm"),
    "manutenção industrial": ("manutenção industrial", "manutencao industrial", "máquina", "maquina"),
    "contratos de manutenção": ("contrato", "recorrente", "preventiva"),
    "Smart360": ("smart360", "ordem de serviço", "os", "dashboard"),
    "sistemas web com IA": (
        "sistema web",
        "sistemas web",
        "sistema logistico",
        "sistema logístico",
        "sistema proprio",
        "sistema próprio",
        "gestao operacional",
        "gestão operacional",
        "entregas",
        "logistica",
        "logística",
        "fretes",
        "rotas",
        "frota",
        "motoristas",
        "on demand",
        "saas",
        "crm",
        "dashboard",
        "portal",
        "planilha",
        "automação de processo",
        "automacao de processo",
        "ia no sistema",
        "ia integrada",
    ),
    "sistemas, sites e soluções digitais": ("site", "django", "python", "digital"),
}


class LiviaAIClient(ABC):
    @abstractmethod
    def generate_reply(self, *, system_prompt, messages, context=None) -> str:
        raise NotImplementedError


class FallbackLiviaAIClient(LiviaAIClient):
    def generate_reply(self, *, system_prompt, messages, context=None) -> str:
        user_text = _last_user_message(messages)
        normalized = _normalize(user_text)
        lead_detected = bool((context or {}).get("lead_detected")) or is_lead_capture_intent(normalized) or is_lead_data_message(user_text)
        handoff_recommended = bool((context or {}).get("handoff_recommended")) or is_real_emergency(normalized)
        service_interest = (context or {}).get("service_interest") or _detect_service_interest(normalized)
        knowledge_context = (context or {}).get("knowledge_context", "")

        if handoff_recommended:
            return (
                "Pelo que você descreveu, há indício de risco real para pessoas e equipamento. "
                "Interrompa a operação com segurança, isole a área e acione a equipe técnica imediatamente. "
                "Se houver risco elétrico, incêndio ou vazamento de gás, siga o protocolo de emergência da planta e acione atendimento humano."
            )

        if is_clear_technical_issue(normalized):
            technical_reply = build_clear_technical_issue_answer(normalized)
            if lead_detected and not bool((context or {}).get("qualified_cycle_locked")):
                known = _collect_known_contact_fields(messages)
                question = _lead_field_question(first_missing_required_field(_known_contact_snapshot(known)), known)
                return f"{technical_reply}\n\nPara encaminhar corretamente, {question[:1].lower() + question[1:]}"
            if bool((context or {}).get("locked_technical_followup")):
                return f"{technical_reply}\n\nAnotei essa informação técnica adicional no seu atendimento."
            return technical_reply

        if bool((context or {}).get("locked_technical_followup")):
            return "Perfeito, adicionei essa nota técnica ao seu atendimento. Nossa equipe já vai avaliar esse detalhe adicional."


        if bool((context or {}).get("conversation_already_notified")):
            notified_reply = build_notified_commercial_followup_reply(
                normalized,
                messages,
                lead_detected=lead_detected,
            )
            if notified_reply:
                return notified_reply

        if bool((context or {}).get("qualified_cycle_locked")):
            post_qualified_reply = build_post_qualified_followup_reply(normalized)
            if post_qualified_reply:
                return post_qualified_reply

        if is_price_question(normalized):
            if _has_xyron_context(normalized, messages):
                return (
                    "Preço, prazo, estoque e disponibilidade dos robôs Xyron dependem do modelo, configuração, acessórios e escopo de implantação. "
                    "Para evitar uma resposta absoluta, eu preciso validar com a equipe comercial/técnica. A vitrine geral fica em /solucoes/xyron-robotics/."
                )
            if is_web_system_context(messages, normalized):
                return build_web_system_price_answer()
            return (
                "O valor depende da configuração, aplicação, disponibilidade e escopo de implantação. "
                "Para estimar corretamente, preciso entender objetivo, volume de uso, integrações e nível de implantação."
            )

        if _asks_availability(normalized) and _has_xyron_context(normalized, messages):
            if any(term in normalized for term in ("cao robo", "cachorro robo", "robo cachorro", "quadrupede", "buddy", "budy")):
                return (
                    "O Buddy Bot é o cão robô da linha Xyron. Estoque, pronta entrega e prazo precisam ser confirmados conforme configuração e disponibilidade comercial. "
                    "Página interna: /solucoes/xyron-robotics/buddy/. Posso encaminhar a validação com a equipe da Smart Control Brasil?"
                )
            return (
                "Estoque, pronta entrega e prazo dos robôs Xyron precisam ser confirmados conforme modelo e configuração. "
                "Posso direcionar pela vitrine /solucoes/xyron-robotics/ e encaminhar a validação com a equipe comercial/técnica."
            )

        ai_data_reply = build_ai_data_answer(normalized)
        if ai_data_reply:
            return ai_data_reply

        continuation_reply = _build_continuation_reply(normalized, messages)
        if continuation_reply:
            return continuation_reply

        if _is_web_system_capability_question(normalized):
            return build_web_system_capability_answer(normalized, messages)

        if _is_mobile_app_capability_question(normalized):
            return build_mobile_app_capability_answer(normalized, messages)

        qualified_cycle_locked = bool((context or {}).get("qualified_cycle_locked"))
        discovery_active = needs_consultative_discovery(
            messages,
            normalized,
            qualified_cycle_locked=qualified_cycle_locked,
        )
        if discovery_active:
            return build_consultative_discovery_reply(normalized, messages)

        if _is_locality_question(normalized) or _is_visit_request(normalized):
            return build_lead_collection_reply(normalized, messages, service_interest)

        if _should_continue_lead_collection(normalized, messages):
            return build_lead_collection_reply(normalized, messages, service_interest)

        recent_product = str((context or {}).get("recent_product") or "").strip().lower()
        if knowledge_context:
            product_reply = _reply_from_knowledge(knowledge_context, normalized, recent_product=recent_product)
            if product_reply:
                return product_reply

        if _looks_like_unknown_robot_model(normalized):
            return (
                "Não encontrei esse modelo na base atual da Smart Control Brasil. "
                "Você quis dizer LIRO/LittleBot, NeoBot, HygiBot, Patrol/Orbit, Buddy Bot, WaiterBot, CareBot, HostBot ou MowerBot?"
            )

        if is_maintenance_question(normalized) and not lead_detected:
            return build_maintenance_answer(normalized, knowledge_context)

        if lead_detected or (
            discovery_minimum_met(messages, normalized)
            and conversation_has_open_solution_need(messages)
            and not qualified_cycle_locked
        ):
            if not discovery_active and not bool((context or {}).get("conversation_already_notified")):
                return build_lead_collection_reply(normalized, messages, service_interest)

        if _asks_for_price(normalized):
            return (
                "O valor depende da configuração, da aplicação, da disponibilidade e do escopo de implantação. "
                "Se você quiser, faço uma pré-análise rápida e já encaminho para a equipe da Smart Control Brasil montar a proposta."
            )

        if _is_mitsubishi_motors_topic(normalized):
            return (
                "Este atendimento é da Smart Control Brasil para Mitsubishi Electric em automação industrial, não para veículos da Mitsubishi Motors. "
                "Se quiser, posso te orientar sobre CLPs MELSEC, IHMs, inversores, servos, motion e robôs MELFA."
            )

        if _is_robot_recommendation_question(normalized):
            recommendation = _recommend_robot_by_scenario(normalized)
            if recommendation:
                return recommendation

        if _is_automation_diagnostic_question(normalized):
            return (
                "Perfeito. Para te direcionar com mais precisão, me conta: qual máquina ou processo está envolvido, "
                "qual problema atual vocês enfrentam, se já existe painel/CLP/IHM/inversor/servo, qual urgência e qual objetivo principal."
            )

        if knowledge_context:
            rag_reply = build_rag_based_fallback(normalized, knowledge_context)
            if rag_reply:
                return rag_reply

        if "smart360" in normalized:
            return (
                "O Smart360 é a frente da Smart Control Brasil para gestão operacional, ordens de serviço, ativos e indicadores, "
                "com evolução em pré-lançamento e implantação assistida. Você quer avaliar gestão de OS, manutenção ou dashboards?"
            )

        if bool((context or {}).get("qualified_cycle_locked")):
            return "Perfeito. Registrei essa informação como um complemento à sua solicitação já encaminhada. A equipe avaliará os detalhes."

        return (
            "Sou a Lívia, assistente da Smart Control Brasil. Posso ajudar com automação industrial, robótica Xyron, "
            "Mitsubishi Electric, integração de sistemas, manutenção técnica e soluções digitais. "
            "Me diga o equipamento, aplicação ou problema que você quer avaliar."
        )


class OpenAILiviaAIClient(LiviaAIClient):
    def __init__(self, fallback_client=None):
        self.fallback_client = fallback_client or FallbackLiviaAIClient()

    def generate_reply(self, *, system_prompt, messages, context=None) -> str:
        api_key = getattr(settings, "OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            logger.warning("Lívia OpenAI provider configured without OPENAI_API_KEY; using fallback.")
            return self.fallback_client.generate_reply(
                system_prompt=system_prompt,
                messages=messages,
                context=context,
            )

        try:
            from openai import OpenAI
        except ImportError:
            logger.warning("Lívia OpenAI provider configured but openai package is not installed; using fallback.")
            return self.fallback_client.generate_reply(
                system_prompt=system_prompt,
                messages=messages,
                context=context,
            )

        try:
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=getattr(settings, "LIVIA_AI_MODEL", "gpt-4o-mini"),
                messages=[{"role": "system", "content": _system_prompt_with_context(system_prompt, context)}, *messages],
                temperature=getattr(settings, "LIVIA_AI_TEMPERATURE", 0.4),
                max_tokens=getattr(settings, "LIVIA_AI_MAX_TOKENS", 500),
            )
            reply = (response.choices[0].message.content or "").strip()
            if reply:
                return reply
        except Exception as exc:  # pragma: no cover - defensive network/provider guard
            logger.warning("Lívia OpenAI provider failed; using fallback. Error type: %s", exc.__class__.__name__)

        return self.fallback_client.generate_reply(
            system_prompt=system_prompt,
            messages=messages,
            context=context,
        )


def get_livia_ai_client():
    provider = str(getattr(settings, "LIVIA_AI_PROVIDER", "fallback") or "fallback").lower()
    if provider == "openai":
        return OpenAILiviaAIClient()
    return FallbackLiviaAIClient()


def _last_user_message(messages):
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")
    return ""


def _normalize(text):
    normalized = (text or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", normalized)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return normalized


def _detect_service_interest(normalized_text):
    for service, keywords in SERVICE_KEYWORDS.items():
        if any(keyword in normalized_text for keyword in keywords):
            return service
    return ""


def _system_prompt_with_context(system_prompt, context=None):
    context = context or {}
    knowledge_context = context.get("knowledge_context", "")
    qualified_cycle_locked = context.get("qualified_cycle_locked", False)
    
    prompt = system_prompt.rstrip()
    
    if qualified_cycle_locked:
        prompt += (
            "\n\nIMPORTANTE: Os dados do cliente já foram coletados nesta conversa e a solicitação inicial já foi encaminhada. "
            "Sob nenhuma hipótese peça novamente nome, empresa, telefone, WhatsApp, e-mail ou cidade. "
            "Se o usuário demonstrar interesse em serviço adicional, proposta complementar, contrato de manutenção, "
            "assistência técnica, treinamento, acessórios, peças ou outro produto, registre como complemento da "
            "solicitação existente e continue a conversa normalmente."
        )

    if knowledge_context:
        prompt += (
            "\n\nUse o contexto abaixo como apoio. Se ele não for suficiente, seja transparente e faça uma pergunta objetiva.\n"
            f"{knowledge_context}"
        )
        
    return prompt


def _summarize_knowledge_context(knowledge_context):
    lines = [line.strip("- ") for line in knowledge_context.splitlines() if line.startswith("- ")]
    if not lines:
        return ""
    first = lines[0]
    if len(first) > 260:
        first = first[:257].rstrip() + "..."
    return first



XYRON_DETAIL_LINKS = {
    "liro": "/solucoes/xyron-robotics/liro-littlebot/",
    "littlebot": "/solucoes/xyron-robotics/liro-littlebot/",
    "neobot": "/solucoes/xyron-robotics/neobot/",
    "neo": "/solucoes/xyron-robotics/neobot/",
    "buddy": "/solucoes/xyron-robotics/buddy/",
    "patrol": "/solucoes/xyron-robotics/patrol-orbit/",
    "orbit": "/solucoes/xyron-robotics/patrol-orbit/",
    "hygibot": "/solucoes/xyron-robotics/hygibot/",
    "hygi": "/solucoes/xyron-robotics/hygibot/",
    "dune": "/solucoes/xyron-robotics/hygibot/",
    "duno": "/solucoes/xyron-robotics/hygibot/",
    "hostbot": "/solucoes/xyron-robotics/hostbot/",
    "host": "/solucoes/xyron-robotics/hostbot/",
    "waiterbot": "/solucoes/xyron-robotics/waiterbot/",
    "waiter": "/solucoes/xyron-robotics/waiterbot/",
    "carebot": "/solucoes/xyron-robotics/carebot/",
    "care": "/solucoes/xyron-robotics/carebot/",
    "mowerbot": "/solucoes/xyron-robotics/mowerbot/",
    "mower": "/solucoes/xyron-robotics/mowerbot/",
}


def _xyron_detail_link_for_text(text, fallback="/solucoes/xyron-robotics/"):
    for term, link in XYRON_DETAIL_LINKS.items():
        if term in text:
            return link
    return fallback


def _is_xyron_technical_spec_question(normalized_text):
    return any(
        term in normalized_text
        for term in (
            "ficha tecnica",
            "especificacao",
            "especificacoes",
            "autonomia",
            "bateria",
            "recarga",
            "carregamento",
            "carregar",
            "tempo de carga",
            "duracao",
            "dura",
            "peso",
            "sensor",
            "sensores",
            "camera",
            "termica",
            "temperatura",
            "velocidade",
            "dimensao",
            "dimensoes",
            "tamanho",
            "altura",
            "medida",
            "certificacao",
            "certificacoes",
        )
    )


def _build_xyron_specs_guardrail(normalized_text, product_text=""):
    link = _xyron_detail_link_for_text(f"{normalized_text} {product_text}")
    return (
        "Os recursos e especificações dos robôs Xyron variam conforme modelo, configuração e escopo de implantação. "
        f"Para evitar passar número desatualizado ou fora de contexto, recomendo ver a página do modelo em {link} e validar a configuração com uma avaliação técnica da Smart Control Brasil."
    )

def _reply_from_knowledge(knowledge_context, normalized_text, recent_product=""):
    lines = [line.strip("- ").strip() for line in knowledge_context.splitlines() if line.startswith("- ")]
    if not lines:
        return ""
    top = lines[0].lower()
    if _is_xyron_technical_spec_question(normalized_text):
        return _build_xyron_specs_guardrail(normalized_text, f"{recent_product} {top}")
    if "xyron robotics - visao geral" in top or "xyron robotics - visão geral" in top:
        return (
            "Temos uma linha Xyron para educação, recepção, segurança, limpeza, atendimento, cuidado assistido, demonstração e áreas externas, "
            "com LIRO/LittleBot, NeoBot, HygiBot, Patrol/Orbit, Buddy, WaiterBot, CareBot, HostBot e MowerBot. "
            "A vitrine geral fica em /solucoes/xyron-robotics/. Para eu te indicar o robô certo, o uso seria em escola, empresa, restaurante, clínica, condomínio, evento ou área externa?"
        )
    if "buddy bot" in top:
        if _asks_availability(normalized_text):
            return (
                "O cão robô da linha Xyron é o Buddy Bot. Ele é indicado para inspeção, segurança patrimonial, resgate e áreas de difícil acesso. "
                "Sobre pronta entrega, eu preciso confirmar disponibilidade e configuração com a equipe da Smart Control Brasil. "
                "Posso encaminhar seu interesse para um especialista?"
            )
        return (
            "O Buddy Bot é um robô quadrúpede da linha Xyron, indicado para inspeção, segurança patrimonial, resgate, engenharia, obras, indústrias e áreas de difícil acesso. "
            "Ele apoia equipes em terrenos irregulares e ambientes hostis, sem substituir análise de risco, operadores ou protocolos humanos de segurança. Página interna: /solucoes/xyron-robotics/buddy/."
        )
    if "neo bot" in top:
        return (
            "O Neo Bot é um robô de recepção e atendimento da linha Xyron, indicado para empresas, eventos, escolas e lojas. "
            "Ele apoia orientação, apresentações e interação com visitantes, sem substituir a equipe de recepção ou atendimento humano. Página interna: /solucoes/xyron-robotics/neobot/."
        )
    if "hygibot" in top:
        return (
            "O HygiBot, também tratado como Dune/Duno Bot em algumas conversas, é o robô de limpeza autônoma da linha Xyron. "
            "Ele combina funções como lavar, varrer, aspirar e passar pano seco, apoiando equipes de limpeza em shoppings, indústrias, hospitais, supermercados, hotéis, academias e grandes áreas internas. "
            "Ele ajuda a padronizar rotinas, mas não substitui supervisão, planejamento de limpeza ou equipe humana. Página interna: /solucoes/xyron-robotics/hygibot/."
        )
    if "neobot" in top or "nebot" in normalized_text or ("neo" in normalized_text and "hostbot" not in normalized_text):
        if "idioma" in normalized_text or "idiomas" in normalized_text:
            return (
                "O NeoBot tem comunicação multilíngue e pode operar em mais de 20 idiomas, "
                "o que ajuda bastante em ambientes com visitantes de perfis diferentes."
            )
        return (
            "O NeoBot é um robô recepcionista inteligente da Xyron para atendimento, recepção e experiências interativas em ambientes de alto fluxo. "
            "Ele apoia a jornada de visitantes e a comunicação institucional, sem substituir atendimento humano em situações sensíveis. Página interna: /solucoes/xyron-robotics/neobot/."
        )
    if "liro - planos de aula" in top or "planos de aula" in top:
        return (
            "O LIRO pode apoiar plano de aula em diferentes faixas etárias, com contação de histórias, atividades de cores e sentimentos, "
            "quiz e dinâmicas gamificadas, sempre com o professor como protagonista e alinhamento à BNCC."
        )
    if "liro - inclusao" in top or "apae" in top:
        return (
            "Sim, o LIRO pode apoiar APAEs e clínicas como ferramenta complementar para inclusão, comunicação e engajamento de públicos neurodivergentes. "
            "Ele não substitui a equipe multidisciplinar; potencializa o trabalho terapêutico e pedagógico."
        )
    if "liro - robo educacional com ia" in top or "liro" in top:
        return (
            "O LIRO é um robô educacional com IA da Xyron que apoia sala de aula, engajamento e mediação pedagógica, "
            "respeitando o planejamento do professor e competências da BNCC. Ele não substitui o professor. Página interna: /solucoes/xyron-robotics/liro-littlebot/."
        )
    if "orbitbot" in top:
        return (
            "O OrbitBot é um robô de segurança autônoma com navegação a laser, patrulha 24/7 e monitoramento contínuo. "
            "Ele apoia equipes de segurança em ambientes amplos que exigem cobertura previsível e preventiva, sem substituir vigilantes, central de monitoramento ou protocolos de emergência. Página interna: /solucoes/xyron-robotics/patrol-orbit/."
        )
    if "liro" in top or "littlebot" in top:
        return (
            "O LIRO, também chamado LittleBot, é um robô educacional inteligente para escolas, famílias, creches e clínicas. "
            "Ele apoia interação, aprendizagem, entretenimento e inclusão, sempre como ferramenta complementar ao professor, família ou equipe multidisciplinar. Página interna: /solucoes/xyron-robotics/liro-littlebot/."
        )
    if "orbit bot" in top or "patrol bot" in top:
        return (
            "O Orbit Bot, também tratado como Patrol Bot, é um robô de segurança para grandes áreas com navegação autônoma e patrulhamento programado. Ele apoia prevenção de riscos e rotinas de monitoramento, mas não substitui vigilantes, análise humana ou resposta a emergências. Página interna: /solucoes/xyron-robotics/patrol-orbit/."
        )
    if "waiterbot" in top:
        return (
            "O WaiterBot é um robô de entrega e apoio operacional para restaurantes, hotéis e supermercados. "
            "Ele apoia entregas internas e retorno de bandejas em pontos definidos, sem substituir garçons, atendimento humano ou gestão da operação. Página interna: /solucoes/xyron-robotics/waiterbot/."
        )
    if "carebot" in top:
        return (
            "O CareBot é um robô assistivo para saúde e cuidado residencial, clínicas, hospitais e farmácias. "
            "Ele pode apoiar chamadas rápidas, teleatendimento, alertas e acompanhamento assistivo, mas não substitui médicos, enfermagem, cuidadores ou avaliação clínica. Página interna: /solucoes/xyron-robotics/carebot/."
        )
    if "hostbot" in top:
        return (
            "O HostBot é um robô host para recepção, eventos e orientação de visitantes. É indicado para empresas, comércios, museus, galerias, concessionárias e bancos, como apoio à experiência presencial e sem substituir equipe humana. Página interna: /solucoes/xyron-robotics/hostbot/."
        )
    if "mowerbot" in top:
        return (
            "O MowerBot é um robô cortador de grama para áreas externas, terrenos irregulares, taludes, jardins, praças e campos. Ele apoia produtividade e segurança operacional no corte de vegetação, mas exige avaliação do terreno e operação responsável. Página interna: /solucoes/xyron-robotics/mowerbot/."
        )
    return ""


def is_real_emergency(normalized_text):
    if any(
        term in normalized_text
        for term in ("choque termico", "choque térmico")
    ):
        return False
    return any(term in normalized_text for term in EMERGENCY_TERMS)


def is_lead_capture_intent(normalized_text):
    return any(term in normalized_text for term in LEAD_INTENT_TERMS)


def is_lead_data_message(text):
    normalized_text = _normalize(text)
    if re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", text, re.IGNORECASE):
        return True
    if re.search(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}", text):
        return True
    signal_terms = (
        "meu nome e",
        "meu nome é",
        "me chamo",
        "sou da",
        "empresa",
        "telefone",
        "whatsapp",
        "cidade",
        "e-mail",
        "email",
    )
    if any(term in normalized_text for term in signal_terms):
        return True
    extracted = _extract_contact_fields_from_text(text)
    if extracted.get("name") or extracted.get("company") or extracted.get("phone") or extracted.get("email"):
        return True
    has_city_with_lead_pattern = bool(extracted.get("city")) and (
        "," in str(text or "")
        and any(term in normalized_text for term in ("meu nome", "me chamo", "sou da", "empresa", "telefone", "whatsapp"))
    )
    return has_city_with_lead_pattern


def is_maintenance_question(normalized_text):
    maintenance_terms = (
        "fmea",
        "tpm",
        "manutencao",
        "manutenção",
        "falha",
        "falhas",
        "confiabilidade",
        "disponibilidade",
        "parada",
        "paradas",
        "maquina",
        "máquina",
        "mtbf",
        "mttr",
        "causa raiz",
        "diagnostico",
        "diagnóstico",
    )
    return any(term in normalized_text for term in maintenance_terms)


def build_maintenance_answer(normalized_text, rag_context):
    if "mtbf" in normalized_text and "mttr" in normalized_text and any(
        term in normalized_text for term in ("diferenca", "diferença")
    ):
        return (
            "MTBF mede o intervalo médio entre falhas. MTTR mede o tempo médio para reparar. "
            "Um equipamento saudável tende a ter MTBF alto e MTTR baixo."
        )
    if "mtbf" in normalized_text:
        return (
            "MTBF significa Mean Time Between Failures, ou Tempo Médio Entre Falhas. "
            "Ele indica, em média, quanto tempo um equipamento opera entre uma falha e outra. "
            "Quanto maior o MTBF, maior tende a ser a confiabilidade. "
            "Na prática, usamos MTBF para identificar equipamentos problemáticos, comparar linhas e priorizar manutenção preventiva ou análise de causa raiz."
        )
    if "mttr" in normalized_text:
        return (
            "MTTR significa Mean Time To Repair, ou Tempo Médio Para Reparo. "
            "Ele mostra quanto tempo, em média, a equipe leva para restaurar o equipamento depois de uma falha. "
            "Quanto menor o MTTR, melhor a capacidade de resposta da manutenção."
        )
    if "fmea" in normalized_text:
        return (
            "FMEA é uma metodologia para mapear modos de falha, efeitos e causas, priorizando ações preventivas antes de gerar parada e perda de produção. "
            "Na manutenção, ele ajuda a definir o que atacar primeiro com base em criticidade e risco operacional. "
            "Você quer aplicar FMEA em uma máquina específica ou em uma linha inteira?"
        )
    if "tpm" in normalized_text:
        return (
            "TPM reduz paradas ao estruturar manutenção autônoma, manutenção planejada, eliminação de perdas e rotina de melhoria contínua entre operação e manutenção. "
            "Na prática, isso reduz falhas repetitivas, melhora disponibilidade e aumenta previsibilidade da produção. "
            "Hoje suas paradas estão mais ligadas a falha recorrente, preventiva insuficiente ou operação?"
        )
    if any(term in normalized_text for term in ("parada", "paradas", "falhas recorrentes", "disponibilidade")):
        return (
            "Quando há muitas paradas, o ponto de partida é separar falhas recorrentes de eventos aleatórios e medir impacto em produção, custo e segurança. "
            "Normalmente analisamos histórico de falhas, MTBF/MTTR, criticidade e causas por elétrica, mecânica, automação e operação para definir um plano com análise de falhas, FMEA e TPM. "
            "Essa máquina para mais por falha elétrica, mecânica, automação ou operação?"
        )
    if rag_context:
        first_snippet = _summarize_knowledge_context(rag_context)
        if first_snippet:
            return (
                f"{first_snippet} "
                "Se você quiser, posso transformar isso em um passo a passo inicial para o seu cenário."
            )
    return (
        "Posso te apoiar com um diagnóstico inicial de manutenção usando histórico de falhas, criticidade e indicadores como MTBF/MTTR para priorizar ações. "
        "Você quer começar por um equipamento específico ou por uma linha de produção?"
    )


def is_clear_technical_issue(normalized_text):
    issue_terms = (
        "ihm apagou",
        "ihm apagada",
        "maquina parada",
        "máquina parada",
        "maquina parou",
        "máquina parou",
        "linha parada",
        "inversor em falha",
        "inversor falha",
        "painel apagou",
        "painel apagado",
        "clp sem comunicacao",
        "clp sem comunicação",
        "clp nao comunica",
        "clp não comunica",
    )
    if any(term in normalized_text for term in issue_terms):
        return True
    if "inversor" in normalized_text and "falha" in normalized_text:
        return True
    if "ihm" in normalized_text and any(term in normalized_text for term in ("apagou", "apagada")):
        return True
    if "painel" in normalized_text and any(term in normalized_text for term in ("apagou", "apagado")):
        return True
    if "clp" in normalized_text and any(term in normalized_text for term in ("sem comunicacao", "sem comunicação", "nao comunica", "não comunica")):
        return True
    return False


def build_clear_technical_issue_answer(normalized_text):
    if "ihm" in normalized_text and any(term in normalized_text for term in ("apagou", "apagada")):
        return (
            "Quando uma IHM apaga, pode ser alimentação elétrica, fonte 24V, cabo, disjuntor/fusível, falha da própria IHM ou problema no painel. "
            "Como envolve sistema elétrico, o ideal é não intervir sem técnico habilitado. "
            "O painel da máquina também apagou ou somente a IHM?"
        )
    if "painel" in normalized_text and any(term in normalized_text for term in ("apagou", "apagado")):
        return (
            "Quando um painel apaga, pode haver falta de alimentação, disjuntor/fusível aberto, fonte com falha, proteção atuada ou problema interno no quadro. "
            "Como envolve elétrica, mantenha o equipamento em condição segura e acione técnico habilitado antes de abrir o painel. "
            "A máquina inteira parou ou apenas o painel ficou sem indicação?"
        )
    if "clp" in normalized_text and any(term in normalized_text for term in ("sem comunicacao", "sem comunicação", "nao comunica", "não comunica")):
        return (
            "CLP sem comunicação pode estar ligado a alimentação, rede industrial, cabo, endereço/configuração, módulo de comunicação ou falha no próprio controlador. "
            "Antes de qualquer intervenção em painel, siga o bloqueio seguro e use técnico habilitado. "
            "A falha aparece em uma IHM/supervisório ou nenhum equipamento comunica com o CLP?"
        )
    if "inversor" in normalized_text and "falha" in normalized_text:
        return (
            "Inversor em falha pode indicar sobrecorrente, subtensão/sobretensão, sobretemperatura, falha de motor, cabo ou parametrização. "
            "Se houver painel energizado, não faça reset ou medições sem procedimento seguro e profissional habilitado. "
            "Qual código de falha aparece no inversor?"
        )
    return (
        "Máquina parada pode envolver alimentação, proteção atuada, falha elétrica, automação, sensores, inversor, CLP/IHM ou condição mecânica. "
        "Se houver painel elétrico envolvido, não intervenha sem técnico habilitado e procedimento de segurança. "
        "A parada começou após algum alarme, queda de energia ou intervenção recente?"
    )


def build_ai_data_answer(normalized_text):
    if not any(term in normalized_text for term in (" ia", "ia ", "inteligencia artificial", "inteligência artificial", "prever falha", "previsao de falha", "previsão de falha")):
        return ""
    if not any(term in normalized_text for term in ("planilha", "dados", "historico", "histórico", "csv", "excel")):
        return ""
    return (
        "Dá para avaliar o uso de IA, mas primeiro precisamos analisar a qualidade dos dados. "
        "Antes de falar em previsão de falhas, precisamos verificar volume, histórico, estrutura, lacunas e consistência dos registros. "
        "A planilha tem datas, equipamento, falha, causa, tempo parado e ação tomada?"
    )


def is_price_question(normalized_text):
    price_terms = (
        "preço",
        "preco",
        "valor",
        "quanto custa",
        "quanto fica",
        "cobram quanto",
        "custa colocar",
        "investimento",
    )
    return any(term in normalized_text for term in price_terms)



def _has_xyron_context(normalized_text, messages=None):
    text = _conversation_text(messages or [], normalized_text)
    return any(
        term in text
        for term in (
            "xyron",
            "robo",
            "robos",
            "robot",
            "liro",
            "littlebot",
            "neobot",
            "buddy",
            "patrol",
            "orbit",
            "hygibot",
            "hostbot",
            "waiterbot",
            "carebot",
            "mowerbot",
        )
    )

def _conversation_text(messages, current_normalized=""):
    parts = [current_normalized]
    for message in messages or []:
        if message.get("role") in {"user", "assistant"}:
            parts.append(_normalize(message.get("content", "")))
    return " ".join(part for part in parts if part)


def is_web_system_context(messages, current_normalized=""):
    corpus = _conversation_text(messages, current_normalized)
    return _has_web_system_signals(corpus)


def _has_web_system_signals(normalized_text):
    web_terms = (
        "sistema web",
        "sistemas web",
        "sistema logistico",
        "sistema logístico",
        "sistema proprio",
        "sistema próprio",
        "sistema novo",
        "desenvolver sistema",
        "desenvolvimento de sistema",
        "plataforma propria",
        "plataforma própria",
        "gestao operacional",
        "gestão operacional",
        "entregas",
        "logistica",
        "logística",
        "fretes",
        "rotas",
        "frota",
        "motoristas",
        "on demand",
        "saas",
        "crm",
        "dashboard",
        "portal",
        "planilha",
        "relatorio",
        "relatório",
        "ia no sistema",
        "ia integrada",
        "automatizar processo",
        "automacao de processo",
        "automação de processo",
    )
    return any(term in normalized_text for term in web_terms)


def is_web_system_project_text(normalized_text):
    return _has_web_system_signals(normalized_text)


def _is_logistics_web_context(normalized_text):
    logistics_terms = (
        "logistica",
        "logística",
        "entregas",
        "fretes",
        "rotas",
        "frota",
        "motoristas",
        "on demand",
        "agendadas",
        "gestao operacional",
        "gestão operacional",
    )
    system_terms = (
        "sistema",
        "plataforma",
        "saas",
        "desenvolvimento",
        "orcamento",
        "orçamento",
    )
    return any(term in normalized_text for term in logistics_terms) and any(
        term in normalized_text for term in system_terms
    )


def _is_consulting_intent(normalized_text):
    return any(
        term in normalized_text
        for term in (
            "consultoria",
            "mentoria",
            "avaliacao de ia",
            "avaliação de ia",
            "diagnostico de ia",
            "diagnóstico de ia",
            "consultoria em inteligencia artificial",
            "consultoria em inteligência artificial",
        )
    )


def _is_system_development_intent(normalized_text):
    return any(
        term in normalized_text
        for term in (
            "sistema web",
            "sistemas web",
            "sistema logistico",
            "sistema logístico",
            "sistema proprio",
            "sistema próprio",
            "sistema novo",
            "desenvolver sistema",
            "desenvolvimento de sistema",
            "plataforma",
            "orcamento para um sistema",
            "orçamento para um sistema",
            "quero orcamento",
            "quero orçamento",
            "mvp",
        )
    )


def build_web_system_price_answer():
    return (
        "O valor depende do escopo. Para estimar corretamente, precisamos entender quais processos o sistema deve automatizar, "
        "quantidade de usuários, telas, relatórios, integrações e se haverá IA. Normalmente começamos definindo um MVP "
        "com as funções essenciais para gerar resultado mais rápido. Qual processo você quer automatizar primeiro?"
    )


def _is_mobile_app_capability_question(normalized_text):
    return any(
        term in normalized_text
        for term in (
            "aplicativos moveis",
            "aplicativos móveis",
            "aplicativo mobile",
            "app mobile",
            "trabalham com aplicativos",
            "trabalha com aplicativos",
            "fazem aplicativos",
            "fazem app",
            "desenvolvem aplicativos",
            "desenvolvem app",
        )
    )


def build_mobile_app_capability_answer(normalized_text, messages):
    del normalized_text, messages
    return (
        "Sim, desenvolvemos aplicativos mobile e sistemas web integrados sob medida para a operação do cliente. "
        "Qual seria a finalidade principal do app: vendas, entregas, atendimento, operação interna ou outro processo?"
    )


def _is_web_system_capability_question(normalized_text):
    if any(
        term in normalized_text
        for term in (
            "voces desenvolvem",
            "vocês desenvolvem",
            "desenvolvem sistemas",
            "desenvolvem sistema",
            "fazem sistema",
            "fazem sistemas",
            "fazer sistema",
            "fazer sistemas",
            "vocês fazem",
            "voces fazem",
            "voces fazer",
            "vocês fazer",
        )
    ):
        return True
    return _has_web_system_signals(normalized_text) and any(
        term in normalized_text for term in ("fazem", "fazer", "desenvolvem", "desenvolver")
    )


def build_web_system_capability_answer(normalized_text, messages):
    corpus = _conversation_text(messages, normalized_text).lower()
    if any(term in corpus for term in ("entrega de alimentos", "entrega de comida", "delivery", "alimentos")):
        return (
            "Sim, desenvolvemos sistemas web sob medida, como painéis administrativos, portais, "
            "sistemas de gestão, integrações e automações. No seu caso, você está pensando no sistema de entrega de alimentos?"
        )
    return (
        "Sim, desenvolvemos sistemas web sob medida, como painéis administrativos, portais, "
        "sistemas de gestão, integrações e automações. Qual processo você quer resolver com esse sistema?"
    )


def _has_ai_term(normalized_text):
    return bool(re.search(r"\bia\b", normalized_text)) or any(
        term in normalized_text
        for term in ("inteligencia artificial", "inteligência artificial", "ia integrada", "ia no sistema")
    )


def web_system_interest_summary(normalized_text):
    digital_summary = build_digital_product_interest_summary(normalized_text)
    if digital_summary:
        return digital_summary

    if _is_consulting_intent(normalized_text) and not _is_system_development_intent(normalized_text):
        return ""

    if _is_logistics_web_context(normalized_text) or (
        _is_system_development_intent(normalized_text) and any(
            term in normalized_text
            for term in ("logistica", "logística", "entregas", "fretes", "rotas", "frota", "motoristas", "on demand")
        )
    ):
        return (
            "Cliente interessado em desenvolvimento de sistema logístico web próprio com IA integrada "
            "para gestão de entregas, rotas, frota/motoristas e fretes."
        )

    if is_web_system_project_text(normalized_text) and _has_ai_term(normalized_text):
        return "Cliente interessado em desenvolvimento de sistema web com IA integrada para automatizar processos/planilhas."
    if any(term in normalized_text for term in ("planilha", "excel")):
        return "Cliente interessado em transformar controle por planilha em sistema web com relatórios e automações."
    if any(term in normalized_text for term in ("crm", "dashboard", "portal")):
        return "Solicitação de CRM/dashboard/portal com possível integração de IA."
    if _has_ai_term(normalized_text) and _is_system_development_intent(normalized_text):
        return "Solicitação de orçamento para desenvolvimento de sistema web com IA integrada."
    if is_web_system_project_text(normalized_text):
        return "Lead interessado em automatizar processo com sistema web."
    return ""


def build_rag_based_fallback(normalized_text, rag_context):
    if is_maintenance_question(normalized_text):
        return build_maintenance_answer(normalized_text, rag_context)

    first_snippet = _summarize_knowledge_context(rag_context)
    if first_snippet:
        return (
            f"{first_snippet} "
            "Se fizer sentido, eu detalho a aplicação prática para o seu ambiente."
        )
    return ""


def build_lead_intent_preface(normalized_text, service_text):
    if is_maintenance_question(normalized_text):
        if "fmea" in normalized_text:
            return (
                "Para orçamento de FMEA, o caminho é mapear modos de falha, efeitos e criticidade para priorizar ações que reduzam parada e risco operacional."
            )
        if "tpm" in normalized_text:
            return (
                "Para orçamento de TPM, começamos avaliando perdas, rotina de manutenção autônoma e manutenção planejada para reduzir falhas e elevar disponibilidade."
            )
        return (
            "Para orçamento/proposta, primeiro alinhamos objetivo técnico, histórico de falhas, escopo e criticidade para montar uma recomendação consistente."
        )
    if any(term in normalized_text for term in ("orcamento", "orçamento", "cotacao", "cotação", "quanto custa")):
        return "Para orçamento, primeiro alinhamos escopo técnico e objetivo para encaminhar a proposta correta."
    return f"Posso te apoiar{service_text} com um direcionamento técnico rápido antes do encaminhamento comercial."


def build_lead_collection_reply(normalized_text, messages, service_interest):
    known = _collect_known_contact_fields(messages)
    service_context = f" para {service_interest}" if service_interest else ""
    locality_question = _is_locality_question(normalized_text)
    visit_request = _is_visit_request(normalized_text)

    next_field = first_missing_required_field(_known_contact_snapshot(known))
    question = _lead_field_question(next_field, known)

    if locality_question:
        current_user_text = _last_user_message(messages)
        city = _extract_contact_fields_from_text(current_user_text).get("city") or known.get("city")
        location_text = f" Para {city}," if city else " Para sua região,"
        return (
            "Atendemos projetos sob avaliação de escopo, urgência e viabilidade técnica."
            f"{location_text} consigo encaminhar uma análise da melhor forma de atendimento, incluindo visita técnica ou suporte remoto. {question}"
        )

    if visit_request:
        return (
            "Podemos avaliar uma visita técnica, sim. Antes de agendar, primeiro alinhamos o cenário e a equipe confirma a melhor forma de atendimento. "
            f"{question}"
        )

    if discovery_minimum_met(messages, normalized_text):
        handoff = build_discovery_to_collection_handoff(normalized_text, messages)
        if handoff:
            return f"{handoff}{question}"

    if _is_first_commercial_without_explicit_data(normalized_text, messages):
        preface = build_lead_intent_preface(normalized_text, service_context)
        return f"{preface} Consigo encaminhar seu interesse para um especialista. {question}"

    return f"Perfeito. {question}"


def _lead_field_question(field, known):
    if field == "name":
        return "Como posso te chamar?"
    if field == "company":
        return "Em qual empresa você trabalha?"
    if field == "phone":
        return "Qual é o melhor telefone/WhatsApp para a equipe falar com você?"
    if field == "email":
        return "Qual e-mail podemos usar para formalizar o atendimento?"
    if field == "city":
        return "Em qual cidade fica sua empresa?"
    return "Qual detalhe técnico você quer avaliar agora?"


def build_post_qualified_followup_reply(normalized_text):
    if any(term in normalized_text for term in ("email", "e-mail")) and any(
        term in normalized_text for term in ("quer", "quer meu", "posso", "informar", "passar")
    ):
        return "Se puder me informar, eu adiciono ao atendimento."
    if "cidade" in normalized_text and any(
        term in normalized_text for term in ("quer", "quer saber", "posso", "informar", "passar")
    ):
        return "Pode me informar a cidade, eu adiciono ao atendimento."
    if normalized_text in {"ok", "obrigado", "obrigada", "valeu", "só isso", "so isso", "somente isso"}:
        return "Perfeito. Atendimento registrado e atualizado. Se precisar, é só me chamar."
    return ""


def build_notified_commercial_followup_reply(normalized_text, messages, *, lead_detected=False):
    from .discovery import (
        build_consultative_discovery_reply,
        needs_consultative_discovery,
    )

    post_qualified_reply = build_post_qualified_followup_reply(normalized_text)
    if post_qualified_reply:
        return post_qualified_reply

    if _is_web_system_capability_question(normalized_text):
        return build_web_system_capability_answer(normalized_text, messages)

    if needs_consultative_discovery(
        messages,
        normalized_text,
        ignore_explicit_forwarding=True,
    ):
        return build_consultative_discovery_reply(normalized_text, messages)

    if lead_detected and (
        _is_logistics_web_context(normalized_text)
        or is_web_system_project_text(normalized_text)
        or any(
            term in normalized_text
            for term in ("entregas", "fretes", "rotas", "frota", "logistica", "logística", "delivery")
        )
    ):
        return (
            "Entendi o novo escopo. Para operações com entregas, rotas, frota e fretes, normalmente estruturamos "
            "pedidos, agendamentos, rastreamento, painel operacional e integrações. "
            "Você quer centralizar tudo em um painel interno ou também abrir para clientes acompanharem pedidos?"
        )

    return ""


def _known_contact_snapshot(known):
    return SimpleNamespace(
        name=known.get("name", ""),
        company=known.get("company", ""),
        city=known.get("city", ""),
        phone=known.get("phone", ""),
        email=known.get("email", ""),
    )


def _is_valid_known_contact_field(field, value):
    validators = {
        "name": _is_valid_name,
        "company": _is_valid_company_or_city,
        "city": _is_valid_company_or_city,
        "phone": _is_valid_phone,
        "email": _is_valid_email,
    }
    validator = validators.get(field)
    if validator is None:
        return False
    return validator(value)


def _collect_known_contact_fields(messages):
    known = {"name": "", "company": "", "city": "", "phone": "", "email": "", "problem": ""}
    expected_field = ""
    for message in messages or []:
        role = message.get("role")
        text = str(message.get("content") or "").strip()
        if role == "assistant":
            expected_field = _requested_lead_field(text)
            continue
        if role != "user" or not text:
            continue
        extracted = _extract_contact_fields_from_text(text)
        for key in ("name", "company", "city", "phone", "email"):
            candidate = extracted.get(key)
            if candidate and not known.get(key) and _is_valid_known_contact_field(key, candidate):
                known[key] = candidate
        if expected_field and not known.get(expected_field):
            conversational_value = _extract_conversational_reply(text, expected_field)
            if conversational_value and _is_valid_known_contact_field(expected_field, conversational_value):
                known[expected_field] = conversational_value
        if extracted.get("problem") and len(extracted["problem"]) > len(known["problem"]):
            known["problem"] = extracted["problem"]
        expected_field = ""
    return known


def _requested_lead_field(text):
    normalized = _normalize(text)
    prompts = (
        ("name", ("como posso te chamar", "qual e o seu nome")),
        ("company", (
            "em qual empresa",
            "qual e a empresa",
            "qual é a empresa",
            "qual o nome da sua empresa",
            "qual é o nome da sua empresa",
            "nome da empresa",
            "nome da sua empresa",
            "agora preciso do nome da empresa",
        )),
        ("phone", ("qual e o melhor telefone", "telefone/whatsapp")),
        ("email", (
            "qual é o melhor e-mail",
            "qual e o melhor e-mail",
            "qual é o seu e-mail",
            "qual e o seu e-mail",
            "qual e-mail podemos usar para formalizar o atendimento",
        )),
        ("city", ("em qual cidade",)),
    )
    for field, markers in prompts:
        if any(marker in normalized for marker in markers):
            return field
    return ""


def _extract_conversational_reply(text, expected_field):
    value = str(text or "").strip(" .,-")
    if expected_field == "phone":
        match = re.search(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}", value)
        return match.group(0) if match else ""
    if expected_field == "email":
        match = re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", value, re.IGNORECASE)
        return match.group(0) if match else ""
    if expected_field not in {"name", "company", "city"} or not value or len(value) > 180:
        return ""
    if re.search(r"[@\d]", value) or "," in value or "?" in value:
        return ""
    if not re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-z0-9À-ÿ .&/'-]{1,179}", value):
        return ""
    if expected_field in {"name", "company", "city"}:
        value = strip_repetition_noise(value)
    return value


def _extract_contact_fields_from_text(text):
    normalized = _normalize(text)
    name_match = re.search(r"(?:meu nome e|me chamo|sou o|sou a|sou)\s+([a-zà-ÿ ]{2,80})", normalized, re.IGNORECASE)
    company_match = re.search(r"(?:empresa|da empresa|trabalho na|sou da)\s+([a-z0-9à-ÿ .&-]{2,100})", normalized, re.IGNORECASE)
    city_match = re.search(r"(?:cidade|estou em|em)\s+([a-zà-ÿ ]{3,80})", normalized, re.IGNORECASE)
    phone_match = re.search(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}", text)
    email_match = re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", normalized, re.IGNORECASE)

    problem = ""
    lower_text = normalized.lower()
    if any(
        term in lower_text
        for term in (
            "parada",
            "falha",
            "manutencao",
            "manutenção",
            "diagnostico",
            "diagnóstico",
            "suporte",
            "fmea",
            "tpm",
            "objetivo",
            "problema",
            "linha",
        )
    ):
        if len(lower_text) >= 45:
            problem = text.strip()[:300]

    city_value = (city_match.group(1).strip(" .,-") if city_match else "")[:80]
    if not city_value:
        city_value = _extract_city_from_csv_like_message(text)

    return {
        "name": (name_match.group(1).strip(" .,-") if name_match else "")[:80],
        "company": (company_match.group(1).strip(" .,-") if company_match else "")[:100],
        "city": city_value,
        "phone": phone_match.group(0).strip() if phone_match else "",
        "email": (email_match.group(0).strip() if email_match else "")[:180],
        "problem": problem,
    }


def _build_continuation_reply(normalized_text, messages):
    if not _is_line_wide_followup(normalized_text):
        return ""

    previous_assistant = _last_assistant_message(messages)
    if not previous_assistant:
        return ""

    previous_normalized = _normalize(previous_assistant)
    asks_scope = any(
        snippet in previous_normalized
        for snippet in (
            "maquina especifica ou em uma linha inteira",
            "máquina específica ou em uma linha inteira",
            "equipamento especifico ou por uma linha de producao",
            "equipamento específico ou por uma linha de produção",
            "aplicar fmea em uma maquina especifica ou em uma linha inteira",
            "aplicar fmea em uma máquina específica ou em uma linha inteira",
        )
    )
    if not asks_scope:
        return ""

    return (
        "Perfeito. Para aplicar FMEA em uma linha inteira, o ideal é dividir a linha por etapas ou subconjuntos: "
        "entrada de material, transporte, processamento, inspeção, embalagem e saída. "
        "Depois mapeamos os principais modos de falha de cada etapa, seus efeitos na produção, causas prováveis, "
        "controles existentes e prioridade de ação. Para começar, me diga qual é a linha e quais são as 3 paradas mais frequentes."
    )


def _is_line_wide_followup(normalized_text):
    return normalized_text in {
        "linha toda",
        "na linha toda",
        "linha inteira",
        "producao toda",
        "produção toda",
        "toda a linha",
    }


def _last_assistant_message(messages):
    for message in reversed(messages or []):
        if message.get("role") == "assistant":
            return str(message.get("content") or "")
    return ""


def _should_continue_lead_collection(normalized_text, messages):
    previous_assistant = _last_assistant_message(messages)
    expected_field = _requested_lead_field(previous_assistant)
    if not expected_field:
        return False
    return bool(_extract_conversational_reply(_last_user_message(messages), expected_field))


def _is_followup_lead_collection(messages):
    return bool(_requested_lead_field(_last_assistant_message(messages)))


def _is_first_commercial_without_explicit_data(normalized_text, messages):
    if not is_lead_capture_intent(normalized_text):
        return False
    if _is_followup_lead_collection(messages):
        return False
    explicit_first_intents = (
        "quero um diagnostico",
        "quero um diagnóstico",
        "preciso de diagnostico",
        "preciso de diagnóstico",
        "quero orcamento",
        "quero orçamento",
        "preciso de manutencao",
        "preciso de manutenção",
    )
    if any(term in normalized_text for term in explicit_first_intents):
        return True
    extracted = _extract_contact_fields_from_text(normalized_text)
    has_explicit_data = any(
        [
            extracted.get("name"),
            extracted.get("company"),
            extracted.get("city"),
            extracted.get("phone"),
            extracted.get("email"),
        ]
    )
    return not has_explicit_data


def _is_locality_question(normalized_text):
    locality_terms = (
        "atendem em",
        "atendem minha regiao",
        "atendem minha região",
        "podem atender em",
        "estou em",
        "podem vir aqui",
        "atendem aqui",
        "minha regiao",
        "minha região",
    )
    return any(term in normalized_text for term in locality_terms)


def _is_visit_request(normalized_text):
    visit_terms = (
        "podem enviar um tecnico",
        "podem enviar um técnico",
        "preciso de tecnico",
        "preciso de técnico",
        "podem vir aqui",
        "fazem visita tecnica",
        "fazem visita técnica",
        "quero uma visita",
        "tecnico para diagnostico",
        "técnico para diagnóstico",
    )
    return any(term in normalized_text for term in visit_terms)


def _extract_city_from_csv_like_message(text):
    raw_text = str(text or "")
    if "," not in raw_text:
        return ""
    normalized_text = _normalize(raw_text)
    has_lead_markers = any(
        term in normalized_text
        for term in ("meu nome", "me chamo", "sou da", "empresa", "telefone", "whatsapp")
    )
    if not has_lead_markers:
        return ""

    chunks = [chunk.strip(" .,-") for chunk in raw_text.split(",") if chunk.strip(" .,-")]
    if not chunks:
        return ""
    blacklist = (
        "meu nome",
        "me chamo",
        "sou da",
        "sou de",
        "empresa",
        "telefone",
        "whatsapp",
        "email",
        "e-mail",
        "diagnostico",
        "diagnóstico",
        "problema",
        "objetivo",
        "@",
    )
    for chunk in chunks:
        lowered = _normalize(chunk)
        if any(term in lowered for term in blacklist):
            continue
        if re.search(r"\d", chunk):
            continue
        if len(chunk) < 3:
            continue
        words = [word for word in chunk.split() if word]
        if 1 <= len(words) <= 3:
            return chunk[:80]
    return ""


def _format_missing_fields(fields):
    if not fields:
        return ""
    if len(fields) == 1:
        return fields[0]
    if len(fields) == 2:
        return f"{fields[0]} e {fields[1]}"
    return ", ".join(fields[:-1]) + f" e {fields[-1]}"


def _asks_for_price(normalized_text):
    return is_price_question(normalized_text)


def _asks_availability(normalized_text):
    return any(term in normalized_text for term in ("pronta entrega", "pronta-entrega", "estoque", "disponivel", "disponibilidade"))


def _is_mitsubishi_motors_topic(normalized_text):
    has_mitsubishi = "mitsubishi" in normalized_text
    has_vehicle_terms = any(term in normalized_text for term in ("carro", "carros", "motos", "motor", "veículo", "veiculo", "motors"))
    return has_mitsubishi and has_vehicle_terms


def _is_robot_recommendation_question(normalized_text):
    if "qual rob" in normalized_text and any(term in normalized_text for term in ("serve", "ideal", "indica", "recomenda")):
        return True
    return any(
        term in normalized_text
        for term in (
            "robo educacional",
            "robo para escola",
            "robo de limpeza",
            "higienizacao",
            "higienização",
            "robo de seguranca",
            "robo de segurança",
            "robo garcom",
            "robo garçom",
            "robo recepcionista",
            "robo para recepcao",
            "robo para recepção",
            "robo para eventos",
            "robo corta grama",
            "robo cortador de grama",
            "cortar grama",
            "cao robo",
            "cachorro robo",
            "robo cachorro",
            "robo quadrupede",
            "demonstracao",
            "demonstração",
            "interacao leve",
            "interação leve",
            "inspecao",
            "inspeção",
            "area dificil",
            "área difícil",
        )
    )


def _is_automation_diagnostic_question(normalized_text):
    return "automa" in normalized_text and any(term in normalized_text for term in ("industrial", "clp", "plc", "ihm", "inversor", "servo"))


def _recommend_robot_by_scenario(normalized_text):
    if any(term in normalized_text for term in ("escola", "educa", "creche", "infantil")):
        return (
            "Para esse cenário, eu avaliaria 1) LIRO/LittleBot para interação e aprendizagem, "
            "2) Neo Bot para recepção interativa e 3) HostBot para ambientes com fluxo de visitantes. "
            "O LIRO não substitui o professor; ele entra como apoio pedagógico. "
            "A escolha depende da faixa etária, objetivo pedagógico e formato de uso no dia a dia. "
            "Página do LIRO: /solucoes/xyron-robotics/liro-littlebot/."
        )
    if any(term in normalized_text for term in ("limpeza", "higienizacao", "higienização", "shopping", "academia", "hospital")):
        return (
            "Para limpeza em áreas internas, o HygiBot/Dune Bot costuma ser o caminho principal. "
            "Ele apoia varrição, aspiração e rotinas programadas, sem substituir supervisão e equipe de limpeza. "
            "Para filtrar melhor, preciso saber área aproximada, tipo de piso e frequência de uso. "
            "Página interna: /solucoes/xyron-robotics/hygibot/."
        )
    if any(term in normalized_text for term in ("segurança", "seguranca", "patrulha", "ronda", "monitoramento", "patrulhamento")):
        return (
            "Para segurança e patrulhamento, as opções mais aderentes costumam ser 1) Orbit Bot/Patrol Bot para grandes áreas internas, "
            "2) Buddy Bot para terreno irregular e áreas externas e 3) HostBot quando a recepção também precisa de orientação. "
            "Esses robôs apoiam a equipe de segurança, mas não substituem vigilantes, central de monitoramento ou protocolos de emergência. "
            "Página do Orbit: /solucoes/xyron-robotics/patrol-orbit/."
        )
    if any(term in normalized_text for term in ("restaurante", "hotel", "bandeja", "entrega", "food", "garcom", "garçom")):
        return (
            "Para operação de entrega interna, o WaiterBot costuma ser a opção principal. "
            "Ele apoia garçons e equipe de salão, sem vender a ideia de substituir todo o atendimento humano. "
            "Dependendo do fluxo, pode ser combinado com Neo Bot ou HostBot na recepção. "
            "Página interna: /solucoes/xyron-robotics/waiterbot/."
        )
    if any(term in normalized_text for term in ("recepcao", "recepção", "recepcionista", "evento", "eventos", "visitante", "visitantes")):
        return (
            "Para recepção e eventos, eu compararia NeoBot e HostBot. "
            "O NeoBot é mais voltado a atendimento e interação inteligente; o HostBot é forte para orientação e presença em eventos. "
            "Eles apoiam a experiência dos visitantes, sem substituir equipe humana. "
            "Links: /solucoes/xyron-robotics/neobot/ e /solucoes/xyron-robotics/hostbot/."
        )
    if any(term in normalized_text for term in ("saude", "saúde", "idoso", "idosos", "clinica", "clínica", "teleatendimento")):
        return (
            "Para saúde e cuidado assistivo, o CareBot é a opção Xyron mais aderente. "
            "Ele pode apoiar teleatendimento, alertas e acompanhamento, mas não substitui médicos, cuidadores ou equipe clínica. "
            "Página interna: /solucoes/xyron-robotics/carebot/."
        )
    if any(term in normalized_text for term in ("grama", "corta grama", "cortador", "talude", "jardim", "area verde", "área verde")):
        return (
            "Para corte de grama, jardim e áreas externas, o MowerBot é o robô indicado. "
            "Ele apoia produtividade e segurança no corte de vegetação, mas depende de avaliação do terreno e da rotina de operação. "
            "Página interna: /solucoes/xyron-robotics/mowerbot/."
        )
    if any(term in normalized_text for term in ("demonstracao", "demonstração", "interacao leve", "interação leve", "inspecao", "inspeção", "area dificil", "área difícil", "quadrupede", "cao robo", "cachorro robo")):
        return (
            "Para demonstração, interação leve, inspeção ou áreas de difícil acesso, o Buddy Bot pode ser a opção Xyron mais aderente. "
            "Ele apoia equipes em inspeções e presença em ambientes complexos, sem substituir operadores, análise de risco ou protocolos humanos. "
            "Página interna: /solucoes/xyron-robotics/buddy/."
        )
    return (
        "Posso te sugerir de 1 a 3 robôs ideais, mas preciso de um contexto rápido: "
        "tipo de ambiente, objetivo principal e se o foco é educação, recepção, segurança, limpeza, entrega, saúde, inspeção ou área externa."
    )


def _looks_like_unknown_robot_model(normalized_text):
    if any(term in normalized_text for term in ("cheiro de queimado", "risco eletrico", "risco elétrico", "incendio", "incêndio", "fumaça", "fumaca", "curto", "choque")):
        return False
    if _is_robot_recommendation_question(normalized_text):
        return False
    if "connectbot" not in normalized_text and "bot" not in normalized_text and "robo" not in normalized_text and "robô" not in normalized_text:
        return False
    known_terms = (
        "liro",
        "little",
        "littlebot",
        "neo",
        "neobot",
        "hygibot",
        "hygi",
        "dune",
        "duno",
        "orbit",
        "patrol",
        "buddy",
        "budy",
        "waiter",
        "carebot",
        "hostbot",
        "mowerbot",
        "xyron",
        "nebot",
    )
    return not any(term in normalized_text for term in known_terms)
