import logging
import re
import uuid
from dataclasses import dataclass

logger = logging.getLogger(__name__)


from django.db import transaction

from .crm_bridge import LiviaCRMBridge
from .integrations import (
    SERVICE_KEYWORDS,
    get_livia_ai_client,
    is_lead_capture_intent,
    is_lead_data_message,
    is_real_emergency,
)
from .knowledge import LiviaKnowledgeService
from .prompts import LIVIA_SYSTEM_PROMPT
from .rag.context_builder import build_context_for_prompt

from .models import LiviaConversation, LiviaHandoffRequest, LiviaLeadCapture, LiviaMessage


@dataclass(frozen=True)
class LiviaResponse:
    reply: str
    lead_detected: bool
    handoff_recommended: bool


class LiviaAssistantService:
    def get_or_create_conversation(self, session_key=None, source_page=""):
        session_key = (session_key or uuid.uuid4().hex).strip()
        conversation = (
            LiviaConversation.objects.filter(
                session_key=session_key,
                status__in=[LiviaConversation.Status.OPEN, LiviaConversation.Status.QUALIFIED],
            )
            .order_by("-created_at")
            .first()
        )
        if conversation is None:
            conversation = LiviaConversation.objects.create(
                session_key=session_key,
                source_page=(source_page or "")[:255],
            )
        elif source_page and not conversation.source_page:
            conversation.source_page = source_page[:255]
            conversation.save(update_fields=["source_page", "updated_at"])
        return conversation

    def register_user_message(self, conversation, content, metadata=None):
        return LiviaMessage.objects.create(
            conversation=conversation,
            role=LiviaMessage.Role.USER,
            content=content.strip(),
            metadata=metadata or {},
        )

    def register_assistant_message(self, conversation, content, metadata=None):
        return LiviaMessage.objects.create(
            conversation=conversation,
            role=LiviaMessage.Role.ASSISTANT,
            content=content.strip(),
            metadata=metadata or {},
        )

    def generate_response(self, conversation, user_text):
        normalized = self._normalize(user_text)
        lead_detected = self.detect_lead_intent(user_text) or self.is_lead_collection_active(conversation)
        handoff_recommended = is_real_emergency(normalized)
        service_interest = self._detect_service_interest(normalized)
        history = self._build_recent_messages(conversation)
        rag_context = build_context_for_prompt(user_text)
        knowledge_context = rag_context or LiviaKnowledgeService().build_context(user_text)
        last_assistant = (
            conversation.messages.filter(role=LiviaMessage.Role.ASSISTANT)
            .order_by("-created_at", "-id")
            .first()
        )
        recent_product = ""
        if last_assistant:
            recent_product = str(last_assistant.metadata.get("product_hint") or "").strip().lower()

        reply = get_livia_ai_client().generate_reply(
            system_prompt=LIVIA_SYSTEM_PROMPT,
            messages=history,
            context={
                "conversation_id": conversation.id,
                "source_page": conversation.source_page,
                "lead_detected": lead_detected,
                "handoff_recommended": handoff_recommended,
                "service_interest": service_interest,
                "knowledge_context": knowledge_context,
                "recent_product": recent_product,
            },
        )

        product_hint = self._infer_product_hint(reply, user_text, knowledge_context, recent_product)

        self.register_assistant_message(
            conversation,
            reply,
            metadata={
                "lead_detected": lead_detected,
                "handoff_recommended": handoff_recommended,
                "session_key": conversation.session_key,
                "knowledge_context_used": bool(knowledge_context),
                "product_hint": product_hint,
            },
        )

        return LiviaResponse(reply=reply, lead_detected=lead_detected, handoff_recommended=handoff_recommended)

    def detect_lead_intent(self, text):
        normalized = self._normalize(text)
        return is_lead_capture_intent(normalized) or is_lead_data_message(text)

    def extract_lead_data(self, text, conversation=None):
        normalized = self._normalize(text)
        email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE)
        phone_match = re.search(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}", text)
        name_match = re.search(r"(?:meu nome é|me chamo|sou o|sou a|sou)\s+([A-Za-zÀ-ÿ ]{2,80})", text, re.IGNORECASE)
        company_match = re.search(r"(?:empresa|da empresa|trabalho na|sou da)\s+([A-Za-z0-9À-ÿ .&-]{2,100})", text, re.IGNORECASE)
        city_match = re.search(r"\b(?:cidade|estou em|em)\s+([A-Za-zÀ-ÿ ]{3,80})", text, re.IGNORECASE)
        compact_name, compact_company = self._extract_compact_lead_identity(text)
        name_value = self._clean_match(name_match) or compact_name
        company_value = self._clean_match(company_match) or compact_company
        expected_field = self._expected_lead_field(conversation)
        conversational_value = self._extract_conversational_field_value(text, expected_field)
        if expected_field == "name" and not name_value:
            name_value = conversational_value
        elif expected_field == "company" and not company_value:
            company_value = conversational_value

        urgency = LiviaLeadCapture.Urgency.MEDIUM
        if is_real_emergency(normalized):
            urgency = LiviaLeadCapture.Urgency.EMERGENCY
        elif any(term in normalized for term in ("alta", "essa semana", "hoje")):
            urgency = LiviaLeadCapture.Urgency.HIGH
        elif any(term in normalized for term in ("sem pressa", "futuro", "planejamento")):
            urgency = LiviaLeadCapture.Urgency.LOW

        service_interest = self._detect_service_interest(normalized)
        if not service_interest and any(
            term in normalized
            for term in (
                "diagnostico",
                "diagnóstico",
                "orcamento",
                "orçamento",
                "manutencao",
                "manutenção",
                "suporte",
                "fmea",
                "tpm",
            )
        ):
            service_interest = "diagnóstico técnico"

        city_value = self._clean_match(city_match)
        if expected_field == "city" and not city_value:
            city_value = conversational_value
        if not city_value:
            city_value = self._extract_city_from_comma_parts(text, excluded_values=(name_value, company_value))

        phone_value = phone_match.group(0) if phone_match else ""
        if expected_field == "phone":
            phone_value = self._extract_relaxed_phone(text) or phone_value

        return {
            "name": name_value,
            "email": email_match.group(0) if email_match else "",
            "phone": phone_value,
            "company": company_value,
            "city": city_value,
            "service_interest": service_interest,
            "urgency": urgency,
            "notes": text.strip(),
        }

    @transaction.atomic
    def create_or_update_lead_capture(self, conversation, extracted_data):
        lead = conversation.lead_captures.order_by("-created_at").first()
        if lead is None:
            lead = LiviaLeadCapture(conversation=conversation)

        for field in ("name", "email", "phone", "company", "city", "service_interest", "notes"):
            value = (extracted_data.get(field) or "").strip()
            if value:
                setattr(lead, field, value)
        if extracted_data.get("urgency"):
            lead.urgency = extracted_data["urgency"]

        self._enrich_lead_from_conversation(lead, conversation)
        lead.is_qualified = bool(lead.name and (lead.phone or lead.email))
        lead.save()

        update_fields = []
        if lead.name and not conversation.visitor_name:
            conversation.visitor_name = lead.name
            update_fields.append("visitor_name")
        if lead.email and not conversation.visitor_email:
            conversation.visitor_email = lead.email
            update_fields.append("visitor_email")
        if lead.phone and not conversation.visitor_phone:
            conversation.visitor_phone = lead.phone
            update_fields.append("visitor_phone")
        if lead.company and not conversation.company_name:
            conversation.company_name = lead.company
            update_fields.append("company_name")
        if lead.is_qualified and conversation.status == LiviaConversation.Status.OPEN:
            conversation.status = LiviaConversation.Status.QUALIFIED
            update_fields.append("status")
        if update_fields:
            update_fields.append("updated_at")
            conversation.save(update_fields=update_fields)

        if lead.is_qualified:
            try:
                LiviaCRMBridge().create_or_update_crm_lead(lead)
            except Exception as exc:  # pragma: no cover - defensive CRM bridge guard
                logger.warning("Lívia CRM bridge failed; lead kept locally. Error type: %s", exc.__class__.__name__)

        return lead

    def build_progressive_lead_reply(self, lead):
        if not lead.name:
            return "Para encaminhar seu pedido, como posso te chamar?"
        if not lead.company:
            return f"Obrigado, {lead.name.split()[0]}. Em qual empresa você trabalha?"
        if not lead.phone and not lead.email:
            return "Qual é o melhor telefone/WhatsApp para nossa equipe falar com você?"
        return self.build_qualified_lead_reply(lead)

    def build_qualified_lead_reply(self, lead):
        first_name = (lead.name or "").split()[0] or ""
        summary = self._build_commercial_context_summary(lead)
        return (
            f"Perfeito, {first_name}. Vou encaminhar seu pedido para nossa equipe com este resumo: {summary}. "
            "Um especialista da Smart Control Brasil entrará em contato."
        )

    def _enrich_lead_from_conversation(self, lead, conversation):
        user_messages = [
            message.content.strip()
            for message in conversation.messages.filter(role=LiviaMessage.Role.USER).order_by("created_at", "id")
            if message.content.strip()
        ]
        if user_messages:
            lead.notes = " | ".join(dict.fromkeys(user_messages))[:4000]
        corpus = " ".join(user_messages)
        normalized = self._normalize(corpus)
        if not lead.city:
            city_match = re.search(r"(?:cidade|em)\s+(São Paulo|Sao Paulo)", corpus, re.IGNORECASE)
            if city_match:
                lead.city = "São Paulo"
        if any(term in normalized for term in ("duno", "dune", "hygibot")):
            lead.service_interest = "Duno - robô de limpeza"
        elif not lead.service_interest:
            lead.service_interest = self._detect_service_interest(normalized)

    def _build_commercial_context_summary(self, lead):
        normalized = self._normalize(lead.notes)
        product = "robô Duno" if any(term in normalized for term in ("duno", "dune", "hygibot")) else "solução solicitada"
        application = " para limpeza noturna" if "limpeza" in normalized and "noturn" in normalized else " para limpeza" if "limpeza" in normalized else ""
        environment = " em supermercado" if "supermercado" in normalized else ""
        area_match = re.search(r"(\d{1,3}(?:[.]\d{3})+|\d+)\s*m(?:²|2)", lead.notes, re.IGNORECASE)
        area = f" de aproximadamente {area_match.group(1)} m²" if area_match else ""
        infrastructure = ", sem infraestrutura de automação atual" if any(term in normalized for term in ("sem infraestrutura", "nao possui infraestrutura", "não possui infraestrutura")) else ""
        city = f", em {lead.city}" if lead.city else ""
        if product != "solução solicitada" or application or environment or area or infrastructure or city:
            return f"{product}{application}{environment}{area}{infrastructure}{city}"
        return lead.service_interest or "solicitação comercial registrada"

    def _extract_relaxed_phone(self, text):
        value = str(text or "").strip()
        if re.fullmatch(r"[+()\d .-]+", value) and 8 <= len(re.sub(r"\D", "", value)) <= 15:
            return value
        return ""

    def create_handoff_request(self, conversation, reason):
        handoff = conversation.handoff_requests.filter(status=LiviaHandoffRequest.Status.PENDING).first()
        if handoff is None:
            handoff = LiviaHandoffRequest.objects.create(conversation=conversation, reason=reason)
        if conversation.status != LiviaConversation.Status.HANDED_OFF:
            conversation.status = LiviaConversation.Status.HANDED_OFF
            conversation.save(update_fields=["status", "updated_at"])
        return handoff

    def _build_recent_messages(self, conversation, limit=10):
        recent_messages = list(conversation.messages.order_by("-created_at", "-id")[:limit])
        return [
            {"role": message.role, "content": message.content}
            for message in reversed(recent_messages)
            if message.role in {LiviaMessage.Role.USER, LiviaMessage.Role.ASSISTANT, LiviaMessage.Role.SYSTEM}
        ]

    def _detect_service_interest(self, normalized_text):
        for service, keywords in SERVICE_KEYWORDS.items():
            if any(keyword in normalized_text for keyword in keywords):
                return service
        return ""

    def _normalize(self, text):
        return (text or "").strip().lower()

    def _clean_match(self, match):
        if not match:
            return ""
        return match.group(1).strip(" .,-")[:180]

    def _looks_like_problem_description(self, text):
        normalized = self._normalize(text)
        return any(
            term in normalized
            for term in (
                "problema",
                "objetivo",
                "falha",
                "falhas",
                "parada",
                "paradas",
                "diagnostico",
                "diagnóstico",
                "suporte",
                "manutencao",
                "manutenção",
                "orcamento",
                "orçamento",
                "linha",
                "maquina",
                "máquina",
            )
        )

    def is_lead_collection_active(self, conversation):
        lead = conversation.lead_captures.order_by("-created_at").first()
        if lead is not None and not lead.is_qualified:
            return True
        return bool(self._expected_lead_field(conversation))

    def _expected_lead_field(self, conversation):
        if conversation is None:
            return ""
        lead = conversation.lead_captures.order_by("-created_at").first()
        if lead is not None and not lead.is_qualified:
            if not lead.name:
                return "name"
            if not lead.company:
                return "company"
            if not lead.phone and not lead.email:
                return "phone"
        last_assistant = conversation.messages.filter(role=LiviaMessage.Role.ASSISTANT).order_by("-created_at", "-id").first()
        if last_assistant is None:
            return ""
        normalized = self._normalize(last_assistant.content)
        prompts = (
            ("name", ("como posso te chamar", "qual é o seu nome", "qual e o seu nome", "informe seu nome", "informar seu nome", "me diga seu nome")),
            ("company", ("qual é a empresa", "qual e a empresa", "em qual empresa")),
            ("phone", ("qual é o melhor telefone", "qual e o melhor telefone", "telefone/whatsapp")),
            ("email", ("qual é o melhor e-mail", "qual e o melhor e-mail", "qual é o seu e-mail", "qual e o seu e-mail")),
            ("city", ("em qual cidade",)),
        )
        for field, markers in prompts:
            if any(marker in normalized for marker in markers):
                return field
        return ""

    def _extract_conversational_field_value(self, text, expected_field):
        value = str(text or "").strip(" .,-")
        if expected_field not in {"name", "company", "city"} or not value or len(value) > 180:
            return ""
        if re.search(r"[@\d]", value) or "," in value or "?" in value:
            return ""
        if not re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-z0-9À-ÿ .&/'-]{1,179}", value):
            return ""
        return value

    def _extract_compact_lead_identity(self, text):
        parts = [part.strip(" .,-") for part in str(text or "").split(",") if part.strip(" .,-")]
        if len(parts) < 3 or not is_lead_data_message(text):
            return "", ""

        name, company = parts[:2]
        labeled_terms = ("meu nome", "me chamo", "sou da", "empresa", "telefone", "whatsapp", "email", "e-mail")
        if any(term in self._normalize(name) or term in self._normalize(company) for term in labeled_terms):
            return "", ""
        if not re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]{1,79}", name):
            return "", ""
        if not re.fullmatch(r"[A-Za-z0-9À-ÿ][A-Za-z0-9À-ÿ .&/'-]{1,99}", company):
            return "", ""
        return name[:180], company[:180]

    def _extract_city_from_comma_parts(self, text, excluded_values=()):
        parts = [part.strip(" .,-") for part in str(text or "").split(",") if part.strip(" .,-")]
        if len(parts) < 2:
            return ""
        excluded = {self._normalize(value) for value in excluded_values if value}
        for part in parts:
            lowered = self._normalize(part)
            if lowered in excluded:
                continue
            if any(term in lowered for term in ("meu nome", "me chamo", "sou da", "empresa", "telefone", "whatsapp", "email", "e-mail")):
                continue
            if re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", part, re.IGNORECASE):
                continue
            if re.search(r"\d", part):
                continue
            words = [token for token in part.split() if token]
            if 1 <= len(words) <= 3:
                return part[:120]
        return ""

    def _infer_product_hint(self, reply, user_text, knowledge_context, recent_product):
        corpus = " ".join([reply or "", user_text or "", knowledge_context or ""]).lower()
        if any(term in corpus for term in ("neo bot", "neobot", "nebot")):
            return "neobot"
        if "hostbot" in corpus:
            return "hostbot"
        if any(term in corpus for term in ("buddy bot", "budy", "cão robô", "cao robo")):
            return "buddy"
        if any(term in corpus for term in ("hygibot", "dune", "duno")):
            return "hygibot"
        if any(term in corpus for term in ("liro", "littlebot")):
            return "liro"
        if any(term in corpus for term in ("orbit", "patrol bot", "orbitbot")):
            return "orbitbot"
        return recent_product
