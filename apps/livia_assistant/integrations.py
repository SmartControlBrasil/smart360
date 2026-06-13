import logging
import os
import re
import unicodedata
from abc import ABC, abstractmethod

from django.conf import settings

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
    "quanto custa",
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
)

SERVICE_KEYWORDS = {
    "PMOC": ("pmoc",),
    "ar-condicionado": ("ar-condicionado", "ar condicionado", "climatização", "climatizacao"),
    "câmaras climáticas": ("câmara", "camara", "climática", "climatica"),
    "equipamentos de academia": ("academia", "esteira", "bike", "musculação", "musculacao"),
    "automação industrial": ("automação", "automacao", "clp", "plc", "ihm"),
    "manutenção industrial": ("manutenção industrial", "manutencao industrial", "máquina", "maquina"),
    "contratos de manutenção": ("contrato", "recorrente", "preventiva"),
    "Smart360": ("smart360", "ordem de serviço", "os", "dashboard", "sistema"),
    "sistemas, sites e soluções digitais": ("site", "sistema", "django", "python", "digital"),
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

        continuation_reply = _build_continuation_reply(normalized, messages)
        if continuation_reply:
            return continuation_reply

        if _is_locality_question(normalized) or _is_visit_request(normalized):
            return build_lead_collection_reply(normalized, messages, service_interest)

        if _should_continue_lead_collection(normalized, messages):
            return build_lead_collection_reply(normalized, messages, service_interest)

        # Quando há intenção explícita de produto, a resposta de conhecimento
        # deve vencer o enquadramento comercial por palavras como "academia".
        recent_product = str((context or {}).get("recent_product") or "").strip().lower()
        if knowledge_context:
            product_reply = _reply_from_knowledge(knowledge_context, normalized, recent_product=recent_product)
            if product_reply:
                return product_reply

        if _looks_like_unknown_robot_model(normalized):
            return (
                "Não encontrei esse modelo na base atual da Smart Control Brasil. "
                "Você quis dizer LIRO/LittleBot, NeoBot, HygiBot, OrbitBot, Buddy Bot, WaiterBot, CareBot, HostBot ou MowerBot?"
            )

        if is_maintenance_question(normalized) and not lead_detected:
            return build_maintenance_answer(normalized, knowledge_context)

        if lead_detected:
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
    knowledge_context = (context or {}).get("knowledge_context", "")
    if not knowledge_context:
        return system_prompt
    return (
        f"{system_prompt.rstrip()}\n\n"
        "Use o contexto abaixo como apoio. Se ele não for suficiente, seja transparente e faça uma pergunta objetiva.\n"
        f"{knowledge_context}"
    )


def _summarize_knowledge_context(knowledge_context):
    lines = [line.strip("- ") for line in knowledge_context.splitlines() if line.startswith("- ")]
    if not lines:
        return ""
    first = lines[0]
    if len(first) > 260:
        first = first[:257].rstrip() + "..."
    return first


def _reply_from_knowledge(knowledge_context, normalized_text, recent_product=""):
    lines = [line.strip("- ").strip() for line in knowledge_context.splitlines() if line.startswith("- ")]
    if not lines:
        return ""
    top = lines[0].lower()
    if "xyron robotics - visao geral" in top or "xyron robotics - visão geral" in top:
        return (
            "A Xyron Robotics é uma empresa de tecnologia robótica com soluções para educação, recepção, atendimento, segurança, limpeza, saúde, entrega, inspeção e operação autônoma. "
            "A Smart Control Brasil conecta essas soluções às aplicações reais do cliente, com diagnóstico, escolha do robô, implantação, treinamento e integração. "
            "As principais linhas incluem LIRO/LittleBot, NeoBot, HygiBot, OrbitBot, Buddy Bot, WaiterBot, CareBot, HostBot e MowerBot."
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
            "Por não depender de rodas, atua melhor em terrenos irregulares e ambientes hostis. "
            "No catálogo: 61 x 37 x 40 cm, 12 kg, autonomia de 2 horas, carregamento em 1 hora, câmera 1920 x 1080 e inclinação máxima de 40°."
        )
    if recent_product == "neobot":
        if any(term in normalized_text for term in ("altura", "dimensao", "dimensoes", "tamanho", "medida", "qual a altura")):
            return (
                "O NeoBot tem dimensões de 45 x 100 x 40 cm. "
                "Considerando essas medidas, a altura aproximada é de 100 cm."
            )
        if "peso" in normalized_text:
            return "O peso informado do NeoBot no catálogo é de 18 kg."
        if "tela" in normalized_text:
            return "O NeoBot possui tela HD de 10,1 polegadas."
        if any(term in normalized_text for term in ("duracao", "dura", "autonomia", "tempo da bateria", "bateria dura")):
            return (
                "O NeoBot tem autonomia de até 10 horas de operação contínua. "
                "A bateria informada no catálogo é de 20.000 mAh."
            )
        if any(term in normalized_text for term in ("recarga", "carregamento", "carregar", "tempo de carga")):
            return "O tempo de carregamento do NeoBot é de aproximadamente 9 horas."
        if "bateria reserva" in normalized_text:
            return (
                "Na base atual não tenho confirmação sobre bateria reserva para o NeoBot. "
                "O catálogo informa bateria de 20.000 mAh, autonomia de até 10 horas e carregamento aproximado de 9 horas. "
                "Para confirmar bateria reserva ou acessórios, preciso validar com a equipe comercial/técnica da Smart Control Brasil."
            )

    if "neo bot" in top:
        return (
            "O Neo Bot é um robô de recepção e atendimento da linha Xyron, indicado para empresas, eventos, escolas e lojas. "
            "Ele oferece interação multilíngue, suporte com IA e experiência interativa para visitantes. "
            "No catálogo: 45 x 100 x 40 cm, 18 kg, tela 10,1 polegadas, bateria de 20.000 mAh, autonomia de até 10 horas e carregamento aproximado de 9 horas."
        )
    if "hygibot" in top:
        return (
            "O HygiBot, também tratado como Dune/Duno Bot em algumas conversas, é o robô de limpeza autônoma da linha Xyron. "
            "Ele combina funções como lavar, varrer, aspirar e passar pano seco, apoiando equipes de limpeza em shoppings, indústrias, hospitais, supermercados, hotéis, academias e grandes áreas internas. "
            "É uma solução indicada para academias e operações com alto fluxo em grandes áreas internas."
        )
    if "neobot" in top or "nebot" in normalized_text or ("neo" in normalized_text and "hostbot" not in normalized_text):
        if any(term in normalized_text for term in ("altura", "dimensao", "dimensoes", "tamanho", "medida")):
            return (
                "O NeoBot tem dimensões de 45 x 100 x 40 cm. "
                "Considerando essas medidas, a altura aproximada é de 100 cm."
            )
        if "peso" in normalized_text:
            return "O peso informado do NeoBot no catálogo é de 18 kg."
        if "tela" in normalized_text:
            return "O NeoBot possui tela HD de 10,1 polegadas."
        if any(term in normalized_text for term in ("duracao", "dura", "autonomia", "tempo da bateria", "bateria dura")):
            return (
                "O NeoBot tem autonomia de até 10 horas de operação contínua. "
                "A bateria informada no catálogo é de 20.000 mAh."
            )
        if any(term in normalized_text for term in ("recarga", "carregamento", "carregar", "tempo de carga")):
            return "O tempo de carregamento do NeoBot é de aproximadamente 9 horas."
        if "bateria reserva" in normalized_text:
            return (
                "Na base atual não tenho confirmação sobre bateria reserva para o NeoBot. "
                "O catálogo informa bateria de 20.000 mAh, autonomia de até 10 horas e carregamento aproximado de 9 horas. "
                "Para confirmar bateria reserva ou acessórios, preciso validar com a equipe comercial/técnica da Smart Control Brasil."
            )
        if "idioma" in normalized_text or "idiomas" in normalized_text:
            return (
                "O NeoBot tem comunicação multilíngue e pode operar em mais de 20 idiomas, "
                "o que ajuda bastante em ambientes com visitantes de perfis diferentes."
            )
        return (
            "O NeoBot é um robô recepcionista inteligente da Xyron para atendimento, recepção e experiências interativas em ambientes de alto fluxo. "
            "Ele combina IA, reconhecimento facial, navegação autônoma, gestão de conteúdo e comunicação multilíngue."
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
            "respeitando o planejamento do professor e competências da BNCC."
        )
    if "orbitbot" in top:
        if "termica" in normalized_text or "temperatura" in normalized_text:
            return (
                "Sim. O OrbitBot possui imagem térmica para vigilância e monitoramento preventivo, "
                "com faixa de temperatura de -5°C a 150°C no catálogo."
            )
        return (
            "O OrbitBot é um robô de segurança autônoma com navegação a laser, patrulha 24/7 e monitoramento contínuo. "
            "Ele é indicado para ambientes amplos que exigem cobertura previsível e preventiva."
        )
    if "liro" in top or "littlebot" in top:
        return (
            "O LIRO, também chamado LittleBot, é um robô educacional inteligente para escolas, famílias, creches e clínicas. "
            "Ele apoia interação, aprendizagem, entretenimento e inclusão, com voz, reconhecimento facial, toque, chamada de vídeo e monitoramento remoto."
        )
    if "orbit bot" in top or "patrol bot" in top:
        return (
            "O Orbit Bot, também tratado como Patrol Bot, é um robô de segurança para grandes áreas com navegação autônoma, patrulhamento programado e identificação visual por IA. "
            "Ele apoia prevenção de riscos com monitoramento em tempo real."
        )
    if "waiterbot" in top:
        return (
            "O WaiterBot é um robô de entrega e apoio operacional para restaurantes, hotéis e supermercados. "
            "Ele navega de forma autônoma, faz entregas em pontos definidos, retorna bandejas e volta automaticamente para carregamento."
        )
    if "carebot" in top:
        return (
            "O CareBot é um robô assistivo para saúde e cuidado residencial, clínicas, hospitais e farmácias. "
            "Ele pode apoiar chamadas rápidas, monitoramento de indicadores, teleatendimento e alertas."
        )
    if "hostbot" in top:
        return (
            "O HostBot é um robô host para recepção e eventos, com duas telas, desvio automático de obstáculos e interação com IA. "
            "É indicado para empresas, comércios, museus, galerias, concessionárias e bancos."
        )
    if "mowerbot" in top:
        return (
            "O MowerBot é um robô cortador de grama por controle remoto para terrenos irregulares e taludes. "
            "Ele aumenta a segurança do operador e a produtividade no corte de vegetação em áreas externas."
        )
    return ""


def is_real_emergency(normalized_text):
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
    if _is_first_commercial_without_explicit_data(normalized_text, messages):
        service_context = f" para {service_interest}" if service_interest else ""
        preface = build_lead_intent_preface(normalized_text, service_context)
        return (
            f"{preface} "
            "Consigo te encaminhar para um especialista da Smart Control Brasil. "
            "Para agilizar, me informe nome, empresa, cidade, telefone/WhatsApp, e-mail e uma breve descrição do problema ou objetivo."
        )

    known = _collect_known_contact_fields(messages)
    missing = []
    if not known.get("name"):
        missing.append("nome")
    if not known.get("company"):
        missing.append("empresa")
    if not known.get("city"):
        missing.append("cidade")
    if not known.get("phone"):
        missing.append("telefone/WhatsApp")
    if not known.get("email"):
        missing.append("e-mail")
    if not known.get("problem"):
        missing.append("breve descrição do problema ou objetivo")

    service_context = f" para {service_interest}" if service_interest else ""
    locality_question = _is_locality_question(normalized_text)
    visit_request = _is_visit_request(normalized_text)
    is_followup = _is_followup_lead_collection(messages)

    missing_text = _format_missing_fields(missing)
    if not missing:
        return (
            f"Perfeito. Já tenho os dados principais{service_context} e consigo te encaminhar para um especialista da Smart Control Brasil. "
            "Se quiser, só complemente com mais detalhes técnicos do cenário para acelerar o diagnóstico."
        )

    if locality_question:
        current_user_text = _last_user_message(messages)
        current_city = _extract_contact_fields_from_text(current_user_text).get("city")
        city = current_city or known.get("city")
        if city:
            return (
                "Atendemos projetos sob avaliação de escopo, urgência e viabilidade técnica. "
                f"Para {city}, consigo encaminhar a análise para um especialista verificar a melhor forma de atendimento, "
                f"seja visita técnica, suporte remoto inicial ou parceiro técnico. Para seguir, me informe {missing_text}."
            )
        return (
            "Atendemos projetos sob avaliação de escopo, urgência e viabilidade técnica. "
            "Consigo encaminhar a análise para um especialista validar a melhor forma de atendimento na sua região. "
            f"Para seguir, me informe {missing_text}."
        )

    if visit_request:
        return (
            "Podemos avaliar uma visita técnica, sim. Antes de agendar, precisamos entender a máquina ou linha, "
            "sintomas, urgência, localização e contato responsável. "
            f"Para seguir, me informe {missing_text}."
        )

    if len(missing) == 1 and missing[0] == "e-mail":
        return "Perfeito. Falta só o e-mail para registrar o atendimento corretamente."
    if len(missing) == 1 and missing[0] == "breve descrição do problema ou objetivo":
        return "Perfeito. Falta só uma breve descrição do problema, equipamento ou objetivo do diagnóstico."
    if set(missing) == {"e-mail", "breve descrição do problema ou objetivo"}:
        return "Perfeito. Para fechar o encaminhamento, falta só seu e-mail e uma breve descrição do problema ou objetivo."

    if is_followup:
        return f"Perfeito. Para seguir, me informe {missing_text}."

    preface = build_lead_intent_preface(normalized_text, service_context)
    return (
        f"{preface} "
        "Consigo te encaminhar para um especialista da Smart Control Brasil. "
        f"Para agilizar, me informe {missing_text}."
    )


def _collect_known_contact_fields(messages):
    known = {"name": "", "company": "", "city": "", "phone": "", "email": "", "problem": ""}
    for message in messages or []:
        if message.get("role") != "user":
            continue
        text = str(message.get("content") or "").strip()
        if not text:
            continue
        extracted = _extract_contact_fields_from_text(text)
        for key in ("name", "company", "city", "phone", "email"):
            if extracted.get(key) and not known.get(key):
                known[key] = extracted[key]
        if extracted.get("problem"):
            if len(extracted["problem"]) > len(known["problem"]):
                known["problem"] = extracted["problem"]
    return known


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
    if not previous_assistant:
        return False
    previous_normalized = _normalize(previous_assistant)
    asked_lead_fields = any(
        snippet in previous_normalized
        for snippet in (
            "para agilizar, me informe",
            "nome, empresa, cidade, telefone",
            "especialista da smart control brasil",
        )
    )
    if not asked_lead_fields:
        return False

    extracted = _extract_contact_fields_from_text(normalized_text)
    if extracted.get("name") or extracted.get("company") or extracted.get("city") or extracted.get("phone") or extracted.get("email"):
        return True

    return bool(re.search(r"\b(nome|empresa|cidade|telefone|whatsapp|whats|zap|email|e-mail)\b", normalized_text))


def _is_followup_lead_collection(messages):
    previous_assistant = _last_assistant_message(messages)
    if not previous_assistant:
        return False
    previous_normalized = _normalize(previous_assistant)
    return "para agilizar, me informe" in previous_normalized or "para seguir, me informe" in previous_normalized


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
    return any(term in normalized_text for term in ("preço", "preco", "valor", "quanto custa", "investimento"))


def _asks_availability(normalized_text):
    return any(term in normalized_text for term in ("pronta entrega", "pronta-entrega", "estoque", "disponivel", "disponibilidade"))


def _is_mitsubishi_motors_topic(normalized_text):
    has_mitsubishi = "mitsubishi" in normalized_text
    has_vehicle_terms = any(term in normalized_text for term in ("carro", "carros", "motos", "motor", "veículo", "veiculo", "motors"))
    return has_mitsubishi and has_vehicle_terms


def _is_robot_recommendation_question(normalized_text):
    return "qual rob" in normalized_text and any(term in normalized_text for term in ("serve", "ideal", "indica", "recomenda"))


def _is_automation_diagnostic_question(normalized_text):
    return "automa" in normalized_text and any(term in normalized_text for term in ("industrial", "clp", "plc", "ihm", "inversor", "servo"))


def _recommend_robot_by_scenario(normalized_text):
    if any(term in normalized_text for term in ("escola", "educa", "creche", "infantil")):
        return (
            "Para esse cenário, eu avaliaria 1) LIRO/LittleBot para interação e aprendizagem, "
            "2) Neo Bot para recepção interativa e 3) HostBot para ambientes com fluxo de visitantes. "
            "A escolha depende da faixa etária, objetivo pedagógico e formato de uso no dia a dia."
        )
    if any(term in normalized_text for term in ("segurança", "patrulha", "ronda", "monitoramento", "patrulhamento")):
        return (
            "Para segurança e patrulhamento, as opções mais aderentes costumam ser 1) Orbit Bot/Patrol Bot para grandes áreas internas, "
            "2) Buddy Bot para terreno irregular e áreas externas e 3) HostBot quando a recepção também precisa de dissuasão e orientação. "
            "Posso te ajudar a filtrar pela área e tipo de risco."
        )
    if any(term in normalized_text for term in ("restaurante", "hotel", "bandeja", "entrega", "food")):
        return (
            "Para operação de entrega interna, o WaiterBot costuma ser a opção principal por navegação autônoma e suporte a múltiplas rotas. "
            "Dependendo do fluxo de atendimento, pode ser combinado com Neo Bot ou HostBot na recepção."
        )
    return (
        "Posso te sugerir de 1 a 3 robôs ideais, mas preciso de um contexto rápido: "
        "tipo de ambiente, objetivo principal e se o foco é educação, recepção, segurança, limpeza, entrega, saúde, inspeção ou área externa."
    )


def _looks_like_unknown_robot_model(normalized_text):
    if any(term in normalized_text for term in ("cheiro de queimado", "risco eletrico", "risco elétrico", "incendio", "incêndio", "fumaça", "fumaca", "curto", "choque")):
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
