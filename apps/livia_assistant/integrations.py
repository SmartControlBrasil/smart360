import logging
import os
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

        if knowledge_context:
            summary = _summarize_knowledge_context(knowledge_context)
            return (
                "Encontrei informações cadastradas na base da Smart Control Brasil que ajudam neste atendimento. "
                f"{summary} Posso te direcionar melhor se você me disser qual equipamento, operação ou unidade precisa de atenção."
            )

        if "smart360" in normalized:
            return (
                "O Smart360 é a frente da Smart Control Brasil para gestão operacional, ordens de serviço, ativos e indicadores, "
                "com evolução em pré-lançamento e implantação assistida. Você quer avaliar gestão de OS, manutenção ou dashboards?"
            )

        return (
            "Olá, sou a Lívia, assistente virtual da Smart Control Brasil. Posso ajudar com manutenção industrial, automação, "
            "ar-condicionado, PMOC, câmaras climáticas, equipamentos de academia, contratos, Smart360 e soluções digitais. "
            "Qual necessidade você quer avaliar primeiro?"
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
    return (text or "").strip().lower()


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
