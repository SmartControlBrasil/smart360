import logging
import os
import re
import unicodedata
from abc import ABC, abstractmethod

from django.conf import settings

logger = logging.getLogger(__name__)


EMERGENCY_TERMS = (
    "emergência",
    "emergencia",
    "urgente",
    "parado",
    "parada",
    "vazamento",
    "gás",
    "gas",
    "risco",
    "queimado",
    "superaquecimento",
    "cheiro de queimado",
    "sem funcionar",
)

LEAD_INTENT_TERMS = (
    "orçamento",
    "orcamento",
    "cotação",
    "cotacao",
    "manutenção",
    "manutencao",
    "preciso",
    "contrato",
    "visita",
    "me chama",
    "whatsapp",
    "zap",
    "contato",
    "pmoc",
    "ar-condicionado",
    "ar condicionado",
    "câmara climática",
    "camara climatica",
    "academia",
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
        lead_detected = bool((context or {}).get("lead_detected")) or any(
            term in normalized for term in LEAD_INTENT_TERMS
        )
        handoff_recommended = bool((context or {}).get("handoff_recommended")) or any(
            term in normalized for term in EMERGENCY_TERMS
        )
        service_interest = (context or {}).get("service_interest") or _detect_service_interest(normalized)
        knowledge_context = (context or {}).get("knowledge_context", "")

        if handoff_recommended:
            return (
                "Entendi. Pelo que você descreveu, pode haver urgência ou risco técnico. "
                "Se houver risco elétrico, vazamento de gás, superaquecimento, cheiro de queimado ou risco estrutural, "
                "interrompa o uso com segurança e fale com nosso atendimento humano pelo WhatsApp. "
                "Para encaminhar melhor, me envie nome, empresa, cidade e telefone."
            )

        if lead_detected:
            service_text = f" sobre {service_interest}" if service_interest else ""
            return (
                f"Posso te ajudar com esse diagnóstico inicial{service_text}. "
                "Para encaminhar corretamente, me informe nome, empresa, cidade, telefone e e-mail. "
                "Não vou passar preços ou prazos fechados por aqui sem avaliação humana."
            )

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
            product_reply = _reply_from_knowledge(knowledge_context, normalized)
            if product_reply:
                return product_reply
            summary = _summarize_knowledge_context(knowledge_context)
            return f"{summary} Se você quiser, eu te ajudo com uma pré-análise do seu cenário."

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
        return "Há contexto interno disponível para orientar a resposta."
    first = lines[0]
    if len(first) > 260:
        first = first[:257].rstrip() + "..."
    return first


def _reply_from_knowledge(knowledge_context, normalized_text):
    lines = [line.strip("- ").strip() for line in knowledge_context.splitlines() if line.startswith("- ")]
    if not lines:
        return ""
    top = lines[0].lower()
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
    if "neo bot" in top:
        return (
            "O Neo Bot é um robô de recepção e atendimento da linha Xyron, indicado para empresas, eventos, escolas e lojas. "
            "Ele oferece interação multilíngue, suporte com IA e experiência interativa para visitantes. "
            "No catálogo: 45 x 100 x 40 cm, 18 kg, tela 10,1 polegadas, bateria de 20.000 mAh, autonomia de até 10 horas e carregamento aproximado de 9 horas."
        )
    if "hygibot" in top:
        return (
            "O HygiBot, também conhecido em alguns contextos como Dune/Duno Bot, é um robô de limpeza autônoma para grandes áreas internas. "
            "Ele combina lavar, varrer, aspirar e passar pano seco, com monitoramento de status e relatórios operacionais."
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
