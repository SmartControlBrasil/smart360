import logging
import re
import uuid
from dataclasses import dataclass

logger = logging.getLogger(__name__)


from django.db import transaction

from .crm_bridge import LiviaCRMBridge
from .lead_extractor import extract_lead_data as universal_extract_lead_data
from .lead_state import LeadState, field_for_state, normalize_state, resolve_state
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
    def get_or_create_conversation(self, session_key=None, source_page="", current_message=""):
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
        elif self._is_lead_cycle_locked(conversation) and not self._is_locked_cycle_continuation_message(current_message):
            # Após qualificação + notificação, iniciamos novo atendimento lógico.
            conversation = LiviaConversation.objects.create(
                session_key=session_key,
                source_page=(source_page or conversation.source_page or "")[:255],
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
        extracted = universal_extract_lead_data(text)
        email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE)
        phone_match = re.search(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}", text)
        name_match = re.search(r"(?:meu nome é|me chamo|sou o|sou a|nome)\s+([A-Za-zÀ-ÿ ]{2,80})", text, re.IGNORECASE)
        company_match = re.search(r"(?:empresa|da empresa|trabalho na|sou da)\s+([A-Za-z0-9À-ÿ .&-]{2,100})", text, re.IGNORECASE)
        city_match = re.search(r"\b(?:cidade|estou em|em)\s+([A-Za-zÀ-ÿ ]{3,80})", text, re.IGNORECASE)
        compact_name, compact_company = self._extract_compact_lead_identity(text)
        name_value = extracted.name or self._clean_match(name_match) or compact_name
        company_value = extracted.company or self._clean_match(company_match) or compact_company
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

        service_interest = extracted.service_interest or self._detect_service_interest(normalized)
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

        city_value = extracted.city or self._clean_match(city_match)
        if expected_field == "city" and not city_value:
            city_value = conversational_value
        if not city_value:
            city_value = self._extract_city_from_comma_parts(text, excluded_values=(name_value, company_value))

        phone_value = extracted.phone or (phone_match.group(0) if phone_match else "")
        if expected_field == "phone":
            phone_value = self._extract_relaxed_phone(text) or phone_value

        return {
            "name": name_value,
            "email": extracted.email or (email_match.group(0) if email_match else ""),
            "phone": phone_value,
            "company": company_value,
            "city": city_value,
            "service_interest": service_interest,
            "urgency": urgency,
            "notes": extracted.technical_context or text.strip(),
            "product_hint": extracted.product_hint,
        }

    @transaction.atomic
    def create_or_update_lead_capture(self, conversation, extracted_data):
        expected_field_before_update = self._expected_lead_field(conversation)
        lead = self._get_active_lead_capture(conversation, extracted_data=extracted_data)
        current_user_message = (
            conversation.messages.filter(role=LiviaMessage.Role.USER)
            .order_by("-created_at", "-id")
            .first()
        )
        first_user_message = (
            conversation.messages.filter(role=LiviaMessage.Role.USER)
            .order_by("created_at", "id")
            .first()
        )
        if lead is None:
            start_message_id = current_user_message.id if current_user_message else None
            if not conversation.lead_captures.exists() and first_user_message:
                start_message_id = first_user_message.id
            lead = LiviaLeadCapture(
                conversation=conversation,
                crm_reference={
                    "capture_start_message_id": start_message_id,
                },
            )
        elif not (lead.crm_reference or {}).get("capture_start_message_id") and current_user_message:
            lead.crm_reference = {**(lead.crm_reference or {}), "capture_start_message_id": current_user_message.id}

        for field in ("name", "email", "phone", "company", "city", "service_interest", "notes"):
            value = (extracted_data.get(field) or "").strip()
            if value:
                existing_value = (getattr(lead, field) or "").strip()
                if field in {"name", "company", "city"} and existing_value:
                    # Evita degradar dado já coletado com resposta curta.
                    if len(value) < len(existing_value):
                        continue
                setattr(lead, field, value)
        if extracted_data.get("urgency"):
            lead.urgency = extracted_data["urgency"]

        self._backfill_contact_fields_from_recent_messages(lead, conversation, current_user_message)
        self._enrich_lead_from_conversation(lead, conversation)
        lead.is_qualified = bool(lead.name and (lead.phone or lead.email))
        if self._is_pending_required_field_unanswered(expected_field_before_update, lead):
            lead.is_qualified = False
        self._persist_lead_state(lead, conversation, extracted_data)
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
        snapshot = self._current_state_snapshot(lead, requires_email=self._requires_email_after_prompt(lead.conversation))
        if snapshot.state == LeadState.COLLECT_NAME:
            return "Para encaminhar seu pedido, como posso te chamar?"
        if snapshot.state == LeadState.COLLECT_COMPANY:
            return f"Obrigado, {lead.name.split()[0]}. Em qual empresa você trabalha?"
        if snapshot.state == LeadState.COLLECT_PHONE:
            return "Qual é o melhor telefone/WhatsApp para nossa equipe falar com você?"
        if snapshot.state == LeadState.COLLECT_EMAIL:
            return "Qual é o melhor e-mail para contato?"
        if snapshot.state == LeadState.QUALIFIED:
            return self.build_qualified_lead_reply(lead)
        return self.build_qualified_lead_reply(lead)

    def build_qualified_lead_reply(self, lead):
        first_name = (lead.name or "").split()[0] or ""
        summary = self._build_commercial_context_summary(lead)
        return (
            f"Perfeito, {first_name}. Vou encaminhar seu pedido para nossa equipe com este resumo: {summary}. "
            "Um especialista da Smart Control Brasil entrará em contato."
        )

    def _enrich_lead_from_conversation(self, lead, conversation):
        start_message_id = (lead.crm_reference or {}).get("capture_start_message_id")
        messages_query = conversation.messages.order_by("created_at", "id")
        if isinstance(start_message_id, int):
            messages_query = messages_query.filter(id__gte=start_message_id)

        all_user_messages = []
        technical_messages = []
        expected_field = ""
        for message in messages_query:
            content = (message.content or "").strip()
            if not content:
                continue
            if message.role == LiviaMessage.Role.ASSISTANT:
                expected_field = self._requested_lead_field_from_assistant(content)
                continue
            if message.role != LiviaMessage.Role.USER:
                continue

            all_user_messages.append(content)
            if self._is_contact_collection_reply(content, expected_field):
                expected_field = ""
                continue
            sanitized = self._sanitize_message_for_notes(content)
            if sanitized:
                technical_messages.append(sanitized)
            expected_field = ""

        selected_messages = technical_messages or all_user_messages
        if selected_messages:
            lead.notes = " | ".join(dict.fromkeys(selected_messages))[:4000]
        corpus = " ".join(selected_messages)
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

    def _requested_lead_field_from_assistant(self, text):
        normalized = self._normalize(text)
        prompts = (
            ("name", ("como posso te chamar", "qual é o seu nome", "qual e o seu nome")),
            ("company", ("em qual empresa", "qual é a empresa", "qual e a empresa")),
            ("phone", ("telefone/whatsapp", "qual é o melhor telefone", "qual e o melhor telefone")),
            ("email", ("qual é o melhor e-mail", "qual e o melhor e-mail", "qual é o seu e-mail", "qual e o seu e-mail")),
            ("city", ("em qual cidade",)),
        )
        for field, markers in prompts:
            if any(marker in normalized for marker in markers):
                return field
        return ""

    def _is_contact_collection_reply(self, text, expected_field):
        value = str(text or "").strip()
        if not expected_field:
            return False
        if expected_field in {"name", "company", "city"}:
            return bool(self._extract_conversational_field_value(value, expected_field))
        if expected_field == "phone":
            return bool(self._extract_relaxed_phone(value) or re.search(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}", value))
        if expected_field == "email":
            return bool(re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", value, re.IGNORECASE))
        return False

    def _sanitize_message_for_notes(self, text):
        value = str(text or "").strip()
        if not value:
            return ""
        if self._looks_like_personal_only_input(value):
            return ""
        if not self._looks_like_problem_description(value):
            return value
        sanitized = re.sub(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", "", value, flags=re.IGNORECASE)
        sanitized = re.sub(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}", "", sanitized)
        sanitized = re.sub(r"\b(?:meu nome é|me chamo|nome)\s+[A-Za-zÀ-ÿ ]{2,80}", "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"\b(?:sou da|empresa|trabalho na)\s+[A-Za-z0-9À-ÿ .&-]{2,100}", "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"\s+", " ", sanitized).strip(" ,.-")
        return sanitized[:300]

    def _backfill_contact_fields_from_recent_messages(self, lead, conversation, current_user_message):
        messages = list(
            conversation.messages.filter(role=LiviaMessage.Role.USER).order_by("created_at", "id")
        )
        if not messages:
            return

        # Janela curta perto da etapa de coleta para evitar puxar histórico irrelevante.
        if current_user_message:
            messages = [m for m in messages if m.id <= current_user_message.id]
        recent_texts = [m.content.strip() for m in messages[-8:] if m.content.strip()]

        if not lead.name:
            multi_word_candidates = [
                text
                for text in reversed(recent_texts)
                if self._extract_conversational_field_value(text, "name")
                and self._looks_like_personal_only_input(text)
                and len(text.split()) >= 2
                and not self._looks_like_problem_description(text)
                and self._normalize(text) not in {"sim", "nao", "não"}
            ]
            if multi_word_candidates:
                lead.name = multi_word_candidates[0]

        if not lead.company:
            for text in reversed(recent_texts):
                candidate = self._extract_conversational_field_value(text, "company")
                if not candidate:
                    continue
                if not self._looks_like_personal_only_input(text):
                    continue
                if self._looks_like_problem_description(candidate):
                    continue
                lowered = self._normalize(candidate)
                if lowered in {"sim", "nao", "não"}:
                    continue
                if lead.name and lowered == self._normalize(lead.name):
                    continue
                lead.company = candidate
                break

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
        lead = self._latest_lead_capture(conversation)
        if lead is not None and self._is_capture_cycle_locked(lead):
            return False
        if lead is not None and not lead.is_qualified:
            return True
        return bool(self._expected_lead_field(conversation))

    def _expected_lead_field(self, conversation):
        if conversation is None:
            return ""
        lead = self._latest_lead_capture(conversation)
        if lead is not None:
            raw_state = (lead.crm_reference or {}).get("lead_state", "")
            state_field = field_for_state(normalize_state(raw_state))
            if state_field:
                return state_field
        if lead is not None and not lead.is_qualified:
            if not lead.name:
                return "name"
            if not lead.company:
                return "company"
            if not lead.phone and not lead.email:
                return "phone"
        if lead is not None and (lead.is_qualified or self._is_capture_cycle_locked(lead)):
            return ""
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
        normalized = self._normalize(value)
        if expected_field == "name":
            value = re.sub(r"^(?:nome|meu nome)\s+", "", value, flags=re.IGNORECASE).strip(" .,-")
            normalized = self._normalize(value)
            forbidden_name_values = {
                "sim",
                "nao",
                "não",
                "limpeza",
                "supermercado",
                "robo",
                "robô",
                "placa",
                "eletronica",
                "eletrônica",
                "diagnostico",
                "diagnóstico",
            }
            if normalized in forbidden_name_values:
                return ""
        if expected_field == "company":
            value = re.sub(r"^(?:empresa|sou da|da)\s+", "", value, flags=re.IGNORECASE).strip(" .,-")
            normalized = self._normalize(value)
            if normalized in {"sim", "nao", "não"}:
                return ""
            if any(term in normalized for term in ("meu nome", "me chamo", "nome")):
                return ""
        if expected_field == "city":
            value = re.sub(r"^(?:cidade|estou em|em)\s+", "", value, flags=re.IGNORECASE).strip(" .,-")
            normalized = self._normalize(value)
            if normalized in {"sim", "nao", "não"}:
                return ""
        if not value:
            return ""
        if not re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-z0-9À-ÿ .&/'-]{1,179}", value):
            return ""
        if expected_field == "company":
            # Evita confundir mensagens de nome com empresa.
            if len(value.split()) >= 3 and "." not in value and "&" not in value:
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

    def _latest_lead_capture(self, conversation):
        return conversation.lead_captures.order_by("-created_at", "-id").first()

    def _is_capture_cycle_locked(self, lead):
        reference = lead.crm_reference or {}
        return bool(
            lead.is_qualified
            and lead.operational_status == LiviaLeadCapture.OperationalStatus.SENT_TO_CRM
            and reference.get("notification_sent_at")
        )

    def _is_lead_cycle_locked(self, conversation):
        latest = self._latest_lead_capture(conversation)
        if latest is None:
            return False
        return self._is_capture_cycle_locked(latest)

    def _get_active_lead_capture(self, conversation, extracted_data=None):
        lead = self._latest_lead_capture(conversation)
        if lead is None:
            return None
        if self._is_capture_cycle_locked(lead):
            if self._has_meaningful_lead_update(extracted_data or {}):
                return lead
            return None
        if lead.is_qualified:
            return None
        return lead

    def _has_meaningful_lead_update(self, extracted_data):
        if any((extracted_data.get(field) or "").strip() for field in ("name", "email", "phone", "company", "city", "service_interest")):
            return True
        notes = (extracted_data.get("notes") or "").strip()
        return bool(notes and self._looks_like_problem_description(notes))

    def _is_pending_required_field_unanswered(self, expected_field, lead):
        if not expected_field:
            return False
        field_values = {
            "name": bool((lead.name or "").strip()),
            "company": bool((lead.company or "").strip()),
            "phone": bool((lead.phone or "").strip()),
            "email": bool((lead.email or "").strip()),
        }
        if expected_field not in field_values:
            return False
        return not field_values[expected_field]

    def _requires_email_after_prompt(self, conversation):
        if conversation is None:
            return False
        last_assistant = (
            conversation.messages.filter(role=LiviaMessage.Role.ASSISTANT)
            .order_by("-created_at", "-id")
            .first()
        )
        if last_assistant is None:
            return False
        normalized = self._normalize(last_assistant.content)
        return "e-mail" in normalized or "email" in normalized

    def _current_state_snapshot(self, lead, requires_email=False):
        return resolve_state(
            has_intent=True,
            has_name=bool((lead.name or "").strip()),
            has_company=bool((lead.company or "").strip()),
            has_phone=bool((lead.phone or "").strip()),
            has_email=bool((lead.email or "").strip()),
            requires_email=requires_email,
            locked=self._is_capture_cycle_locked(lead),
        )

    def _persist_lead_state(self, lead, conversation, extracted_data):
        requires_email = self._requires_email_after_prompt(conversation)
        snapshot = self._current_state_snapshot(lead, requires_email=requires_email)
        updated_reference = dict(lead.crm_reference or {})
        updated_reference["lead_state"] = snapshot.state
        if extracted_data.get("product_hint"):
            updated_reference["product_hint"] = extracted_data["product_hint"]
        lead.crm_reference = updated_reference

    def _looks_like_personal_only_input(self, text):
        normalized = self._normalize(text)
        if re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE):
            return True
        if re.search(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}", text):
            return True
        if any(marker in normalized for marker in ("meu nome", "me chamo", "sou da", "empresa", "telefone", "whatsapp", "email", "e-mail")):
            return True
        technical_markers = (
            "robo",
            "robô",
            "limpeza",
            "supermercado",
            "placa",
            "eletronic",
            "iot",
            "retrofit",
            "falha",
            "parada",
            "diagnost",
            "manutenc",
            "infraestrutura",
            "m²",
            "m2",
        )
        if any(marker in normalized for marker in technical_markers):
            return False
        if re.search(r"\d+\s*m(?:²|2)", text, re.IGNORECASE):
            return False
        words = [w for w in normalized.split() if w]
        return 1 <= len(words) <= 3

    def _is_locked_cycle_continuation_message(self, text):
        normalized = self._normalize(text)
        if not normalized:
            return False
        continuation_markers = (
            "meu nome",
            "me chamo",
            "sou da",
            "empresa",
            "telefone",
            "whatsapp",
            "e-mail",
            "email",
            "problema",
            "objetivo",
        )
        if any(marker in normalized for marker in continuation_markers):
            return True
        if re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text or "", re.IGNORECASE):
            return True
        if re.search(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}", text or ""):
            return True
        # Permite correções curtas de nome/empresa após fechamento técnico/comercial.
        candidate = str(text or "").strip(" .,-")
        if self._looks_like_personal_only_input(candidate) and self._extract_conversational_field_value(candidate, "name"):
            return True
        if self._looks_like_personal_only_input(candidate) and self._extract_conversational_field_value(candidate, "company"):
            return True
        return False
