import logging
import re
import uuid
from dataclasses import dataclass

logger = logging.getLogger(__name__)


from django.db import transaction

from .crm_bridge import LiviaCRMBridge
from .integrations import EMERGENCY_TERMS, LEAD_INTENT_TERMS, SERVICE_KEYWORDS, get_livia_ai_client
from .knowledge import LiviaKnowledgeService
from .prompts import LIVIA_SYSTEM_PROMPT

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
        lead_detected = self.detect_lead_intent(user_text)
        handoff_recommended = any(term in normalized for term in EMERGENCY_TERMS)
        service_interest = self._detect_service_interest(normalized)
        history = self._build_recent_messages(conversation)
        knowledge_context = LiviaKnowledgeService().build_context(user_text)
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
        return any(term in normalized for term in LEAD_INTENT_TERMS)

    def extract_lead_data(self, text):
        normalized = self._normalize(text)
        email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE)
        phone_match = re.search(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}", text)
        name_match = re.search(r"(?:meu nome é|me chamo|sou o|sou a|sou)\s+([A-Za-zÀ-ÿ ]{2,80})", text, re.IGNORECASE)
        company_match = re.search(r"(?:empresa|da empresa|trabalho na|sou da)\s+([A-Za-z0-9À-ÿ .&-]{2,100})", text, re.IGNORECASE)
        city_match = re.search(r"(?:cidade|em|de)\s+([A-Za-zÀ-ÿ ]{3,80})", text, re.IGNORECASE)

        urgency = LiviaLeadCapture.Urgency.MEDIUM
        if any(term in normalized for term in ("emergência", "emergencia", "urgente", "parado", "sem funcionar")):
            urgency = LiviaLeadCapture.Urgency.EMERGENCY
        elif any(term in normalized for term in ("alta", "essa semana", "hoje")):
            urgency = LiviaLeadCapture.Urgency.HIGH
        elif any(term in normalized for term in ("sem pressa", "futuro", "planejamento")):
            urgency = LiviaLeadCapture.Urgency.LOW

        return {
            "name": self._clean_match(name_match),
            "email": email_match.group(0) if email_match else "",
            "phone": phone_match.group(0) if phone_match else "",
            "company": self._clean_match(company_match),
            "city": self._clean_match(city_match),
            "service_interest": self._detect_service_interest(normalized),
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

        lead.is_qualified = bool(lead.name and (lead.phone or lead.email) and lead.service_interest)
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
