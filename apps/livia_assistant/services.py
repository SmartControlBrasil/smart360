import logging
import re
import uuid
from dataclasses import dataclass

logger = logging.getLogger(__name__)


from django.db import transaction

from .crm_bridge import LiviaCRMBridge
from .discovery import (
    conversation_has_open_solution_need,
    discovery_minimum_met,
    needs_consultative_discovery,
)
from .lead_extractor import extract_lead_data as universal_extract_lead_data
from .lead_state import LeadState, LeadStateSnapshot, field_for_state, normalize_state, resolve_state
from .integrations import (
    SERVICE_KEYWORDS,
    get_livia_ai_client,
    is_lead_capture_intent,
    is_lead_data_message,
    is_maintenance_question,
    is_clear_technical_issue,
    is_price_question,
    is_web_system_project_text,
    web_system_interest_summary,
    is_real_emergency,
)
from .knowledge import LiviaKnowledgeService
from .prompts import LIVIA_SYSTEM_PROMPT
from .rag.context_builder import build_context_for_prompt

from .models import LiviaConversation, LiviaHandoffRequest, LiviaLeadCapture, LiviaMessage
from .qualification import (
    INVALID_GENERIC_VALUES,
    INVALID_COMPANY_OR_CITY_SNIPPETS,
    INVALID_NAME_SNIPPETS,
    _is_valid_company_or_city,
    _is_valid_email,
    _is_valid_name,
    _is_valid_phone,
    first_missing_required_field,
    has_valid_city_field,
    has_valid_company_field,
    has_valid_email_field,
    has_valid_name_field,
    has_valid_phone_field,
    is_lead_ready_for_notification,
    strip_repetition_noise,
)
from .technical_summary import (
    build_technical_service_summary,
    extract_technical_context,
    technical_corpus_from_lead,
)


@dataclass(frozen=True)
class LiviaResponse:
    reply: str
    lead_detected: bool
    handoff_recommended: bool


class LiviaAssistantService:
    COMPANY_ASSISTANT_MARKERS = (
        "em qual empresa",
        "qual é a empresa",
        "qual e a empresa",
        "qual o nome da sua empresa",
        "qual é o nome da sua empresa",
        "nome da empresa",
        "nome da sua empresa",
        "agora preciso do nome da empresa",
    )

    INVALID_COMPANY_OR_CITY_VALUES = {
        "sim",
        "sim gostaria",
        "gostaria",
        "ok",
        "pode ser",
        "nao informado",
        "não informado",
        "nao informada",
        "não informada",
    }

    INVALID_CITY_VALUES = {
        "celular",
        "computador",
        "ambos",
        "tablet",
        "sistema",
        "app",
        "aplicativo",
        "estoque",
        "vendas",
        "atendimento",
        "entrega",
        "caderno",
        "anotacao",
        "anotação",
        "planilha",
        "excel",
        "operacao",
        "operação",
        "cliente",
        "clientes",
        "frota",
        "manutencao",
        "manutenção",
        "pedido",
        "pedidos",
    }

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
        lead_detected = (
            (
                self.detect_lead_intent(user_text)
                and not self.needs_consultative_discovery_for_conversation(conversation, user_text)
            )
            or self.is_lead_collection_active(conversation)
            or self._should_resume_lead_capture_after_discovery(conversation)
        )
        handoff_recommended = is_real_emergency(normalized)
        service_interest = self._detect_service_interest(normalized)
        history = self._build_messages_since_notification(conversation)
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
        locked_lead = self.get_locked_lead_capture(conversation)
        system_need_candidate = "sistema" in normalized and any(
            term in normalized
            for term in ("interessado", "interesse", "criar", "preciso", "quero", "marmoraria", "deposito", "depósito")
        )
        commercial_cycle_candidate = (
            self.detect_lead_intent(user_text)
            or is_web_system_project_text(normalized)
            or self._looks_like_problem_description(user_text)
            or system_need_candidate
        )
        starts_new_cycle = self.should_start_new_commercial_cycle(conversation, user_text, locked_lead)
        if starts_new_cycle:
            locked_lead = None

        locked_technical_followup = self.should_append_technical_followup_to_locked_lead(
            conversation, user_text, locked_lead=explicit_lead if "explicit_lead" in locals() else locked_lead
        )

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
                "qualified_cycle_locked": bool(locked_lead),
                "conversation_already_notified": (
                    self._conversation_was_notified(conversation) and not starts_new_cycle and not commercial_cycle_candidate
                ),
                "locked_technical_followup": locked_technical_followup,
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

    def should_collect_explicit_contact_message(self, message):
        normalized = self._normalize(message)
        return is_lead_data_message(message) or is_lead_capture_intent(normalized)

    def needs_consultative_discovery_for_conversation(self, conversation, message=""):
        messages = self._build_messages_since_notification(conversation)
        normalized = self._normalize(message)
        locked_lead = self.get_locked_lead_capture(conversation)
        return needs_consultative_discovery(
            messages,
            normalized,
            qualified_cycle_locked=bool(locked_lead),
            ignore_explicit_forwarding=self._conversation_was_notified(conversation),
        )

    def should_append_technical_followup_to_locked_lead(self, conversation, message, *, locked_lead=None):
        lead = locked_lead or self.get_locked_lead_capture(conversation)
        if lead is None:
            return False
        normalized = self._normalize(message)
        if self.should_start_new_commercial_cycle(conversation, message, lead):
            return False
        if self.should_capture_post_qualified_update_for_conversation(message, conversation):
            return False
        return is_clear_technical_issue(normalized) or (
            self._conversation_was_notified(conversation)
            and self._looks_like_problem_description(message)
            and not self.detect_lead_intent(message)
        )

    def should_continue_conversation_after_notification(self, conversation, *, lead_registered=False):
        return (
            self._conversation_was_notified(conversation)
            and self._conversation_has_complete_contact(conversation)
            and not lead_registered
        )

    def build_notified_context_ack_phrase(self):
        return "Como já temos seus dados, vou acrescentar esse contexto ao atendimento."

    def should_append_notified_context_ack(self, conversation):
        recent_assistant_messages = (
            conversation.messages.filter(role=LiviaMessage.Role.ASSISTANT)
            .order_by("-created_at", "-id")[:3]
        )
        for message in recent_assistant_messages:
            lowered = (message.content or "").lower()
            if "acrescentar" in lowered or "já temos seus dados" in lowered:
                return False
        return True

    def _build_messages_since_notification(self, conversation, limit=20):
        from django.utils.dateparse import parse_datetime
        from django.utils import timezone

        open_lead = self.get_open_lead_capture(conversation)
        cycle_start_id = (open_lead.crm_reference or {}).get("capture_start_message_id") if open_lead else None
        locked = None if open_lead else self.get_locked_lead_capture(conversation)
        cutoff = None
        if locked:
            sent_raw = (locked.crm_reference or {}).get("notification_sent_at")
            if sent_raw:
                cutoff = parse_datetime(sent_raw)
                if cutoff and timezone.is_naive(cutoff):
                    cutoff = timezone.make_aware(cutoff)

        recent_messages = list(conversation.messages.order_by("-created_at", "-id")[: limit * 2])
        filtered = []
        for message in reversed(recent_messages):
            if message.role not in {
                LiviaMessage.Role.USER,
                LiviaMessage.Role.ASSISTANT,
                LiviaMessage.Role.SYSTEM,
            }:
                continue
            if cycle_start_id and message.id < cycle_start_id:
                continue
            if cutoff and message.created_at and message.created_at < cutoff:
                continue
            filtered.append({"role": message.role, "content": message.content})
        return filtered[-limit:]

    def should_start_contact_collection(self, conversation, message):
        if self.needs_consultative_discovery_for_conversation(conversation, message):
            return False
        if self._should_resume_lead_capture_after_discovery(conversation):
            return True
        if self.should_capture_post_qualified_update_for_conversation(message, conversation):
            return True
        if self.is_lead_collection_active(conversation):
            return True
        return self.should_collect_explicit_contact_message(message)

    def _should_resume_lead_capture_after_discovery(self, conversation):
        if self.get_locked_lead_capture(conversation):
            return False
        messages = self._build_recent_messages(conversation)
        return conversation_has_open_solution_need(messages) and discovery_minimum_met(messages)

    def should_update_lead_capture(self, conversation, message):
        if self.is_lead_collection_active(conversation):
            return True
        active_lead = self._get_active_lead_capture(conversation)
        if active_lead is not None and first_missing_required_field(active_lead):
            if self._looks_like_personal_only_input(message) or is_lead_data_message(message):
                return True
        if self.needs_consultative_discovery_for_conversation(conversation, message):
            return is_lead_data_message(message)
        if self.detect_lead_intent(message):
            return True
        lead = self._latest_lead_capture(conversation)
        return lead is not None and not lead.is_qualified and not self._is_capture_cycle_locked(lead)

    def extract_notes_only_lead_data(self, extracted_data):
        notes_only = dict(extracted_data or {})
        for field in ("name", "email", "phone", "company", "city"):
            notes_only[field] = ""
        return notes_only

    def extract_spontaneous_contact_data(self, extracted_data):
        spontaneous = self.extract_notes_only_lead_data(extracted_data)
        for field in ("name", "email", "phone", "company", "city"):
            value = (extracted_data.get(field) or "").strip()
            if value:
                spontaneous[field] = value
        return spontaneous

    def detect_lead_intent(self, text):
        normalized = self._normalize(text)
        if is_price_question(normalized):
            return False
        if self._is_web_system_capability_question(normalized):
            return False
        if is_lead_capture_intent(normalized) or is_lead_data_message(text):
            return True
        if is_maintenance_question(normalized):
            return False
        return self._looks_like_problem_description(text)

    def extract_lead_data(self, text, conversation=None):
        normalized = self._normalize(text)
        extracted = universal_extract_lead_data(text)
        email_match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE)
        phone_match = re.search(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}", text)
        name_match = re.search(r"(?:meu nome é|me chamo|sou o|sou a|nome)\s+([A-Za-zÀ-ÿ ]{2,80})", text, re.IGNORECASE)
        company_match = re.search(r"(?:empresa|da empresa|trabalho na|sou da)\s+([A-Za-z0-9À-ÿ .&-]{2,100})", text, re.IGNORECASE)
        city_match = re.search(r"\b(?:cidade|estou em)\s+([A-Za-zÀ-ÿ ]{3,80})", text, re.IGNORECASE)
        compact_name, compact_company = self._extract_compact_lead_identity(text)
        explicit_name = self._extract_explicit_name(text)
        explicit_company = self._extract_explicit_company(text)
        name_value = explicit_name or (compact_name if compact_name and compact_company else "")
        company_value = explicit_company or (compact_company if compact_name and compact_company else "")
        if self._mentions_name_correction(text) and not explicit_name:
            name_value = ""
            company_value = ""
        if not company_value and "marmoraria" in normalized:
            company_value = "Marmoraria"
        expected_field = self._expected_lead_field(conversation)
        conversational_value = self._extract_conversational_field_value(text, expected_field)
        if expected_field == "name":
            if not self._is_discovery_context_message(text):
                name_value = conversational_value or name_value
                if not name_value:
                    candidate_name = str(text or "").strip()
                    if (
                        len(candidate_name.split()) == 1
                        and _is_valid_name(candidate_name)
                        and not self._is_technical_note_message(self._normalize(candidate_name))
                    ):
                        name_value = candidate_name
        elif expected_field == "company":
            if not self._is_discovery_context_message(text):
                company_value = explicit_company or conversational_value or company_value
                if not company_value:
                    candidate_company = strip_repetition_noise(str(text or "").strip())
                    if (
                        candidate_company
                        and _is_valid_company_or_city(candidate_company)
                        and not self._looks_like_problem_description(candidate_company)
                        and not self._is_technical_note_message(self._normalize(candidate_company))
                        and not (
                            self._is_valid_city_candidate(candidate_company)
                            and len(candidate_company.split()) == 1
                        )
                    ):
                        company_value = candidate_company

        urgency = LiviaLeadCapture.Urgency.MEDIUM
        if is_real_emergency(normalized):
            urgency = LiviaLeadCapture.Urgency.EMERGENCY
        elif any(term in normalized for term in ("alta", "essa semana", "hoje")):
            urgency = LiviaLeadCapture.Urgency.HIGH
        elif any(term in normalized for term in ("sem pressa", "futuro", "planejamento")):
            urgency = LiviaLeadCapture.Urgency.LOW

        service_interest = extracted.service_interest or self._detect_service_interest(normalized)
        if is_web_system_project_text(normalized) or self._is_logistics_web_context(normalized):
            service_interest = self._resolve_web_service_interest_label(normalized)
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
        if not service_interest and is_lead_capture_intent(normalized):
            service_interest = "atendimento técnico"

        city_value = ""
        explicit_city = self._extract_explicit_city(text)
        if explicit_city:
            city_value = explicit_city
        elif expected_field == "city":
            city_value = conversational_value
        elif is_lead_data_message(text):
            comma_city = self._extract_city_from_comma_parts(
                text,
                excluded_values=[name_value, company_value],
            )
            if comma_city:
                city_value = comma_city
        elif (
            conversation
            and self._is_contact_field_collection_phase(conversation)
            and expected_field in {"name", "company", "phone", "email"}
            and not self._message_answers_expected_field(text, expected_field)
        ):
            candidate = strip_repetition_noise(str(text or "").strip())
            excluded = {
                self._normalize(name_value),
                self._normalize(company_value),
            }
            active_lead = self._get_active_lead_capture(conversation)
            if active_lead is not None:
                if active_lead.name:
                    excluded.add(self._normalize(active_lead.name))
                if active_lead.company:
                    excluded.add(self._normalize(active_lead.company))
            if (
                candidate
                and not phone_match
                and "@" not in text
                and len(candidate.split()) <= 3
                and self._is_valid_city_candidate(candidate)
                and self._normalize(candidate) not in excluded
            ):
                city_value = candidate
        if city_value and not self._is_valid_city_candidate(city_value):
            city_value = ""

        phone_value = extracted.phone or (phone_match.group(0) if phone_match else "")
        if expected_field == "phone":
            phone_value = self._extract_relaxed_phone(text) or phone_value

        if name_value and not _is_valid_name(name_value):
            name_value = ""
        if company_value and not _is_valid_company_or_city(company_value):
            company_value = ""

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
    def create_or_update_lead_capture(self, conversation, extracted_data, collecting_contact=True, explicit_lead=None):
        expected_field_before_update = self._expected_lead_field(conversation)
        lead = explicit_lead if explicit_lead is not None else self._get_active_lead_capture(
            conversation, extracted_data=extracted_data
        )
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
            has_locked_cycle = any(
                self._is_capture_cycle_locked(existing)
                for existing in conversation.lead_captures.order_by("-created_at", "-id")
            )
            if has_locked_cycle and current_user_message:
                start_message_id = current_user_message.id
            elif first_user_message:
                start_message_id = first_user_message.id
            else:
                start_message_id = current_user_message.id if current_user_message else None
            lead = LiviaLeadCapture(
                conversation=conversation,
                crm_reference={
                    "capture_start_message_id": start_message_id,
                },
            )
        elif explicit_lead is None and not (lead.crm_reference or {}).get("capture_start_message_id") and current_user_message:
            lead.crm_reference = {**(lead.crm_reference or {}), "capture_start_message_id": current_user_message.id}

        self._seed_lead_contact_from_conversation(lead, conversation)

        visitor_name_cleared = False
        if current_user_message and self._mentions_name_correction(current_user_message.content):
            corrected_name = self._extract_explicit_name(current_user_message.content)
            lead.name = corrected_name if corrected_name and _is_valid_name(corrected_name) else ""
            if not lead.name:
                conversation.visitor_name = ""
                visitor_name_cleared = True
            extracted_data = {
                **(extracted_data or {}),
                "name": lead.name,
                "company": "",
                "city": "",
            }

        if lead.city and not has_valid_city_field(lead):
            lead.city = ""

        if lead.city and lead.name and self._normalize(lead.city) == self._normalize(lead.name):
            lead.city = ""
        if lead.city and lead.company and self._normalize(lead.city) == self._normalize(lead.company):
            lead.city = ""

        if lead.name and lead.company and self._normalize(lead.company) == self._normalize(lead.name):
            lead.company = ""

        for field in ("name", "email", "phone", "company", "city", "service_interest"):
            value = (extracted_data.get(field) or "").strip()
            if value:
                sanitized_value = self._sanitize_lead_field_before_save(field, value)
                if not sanitized_value:
                    if field == "city" and collecting_contact:
                        setattr(lead, field, "")
                    continue
                existing_value = (getattr(lead, field) or "").strip()
                if field in {"name", "company", "city"} and existing_value:
                    existing_validators = {
                        "name": has_valid_name_field,
                        "company": has_valid_company_field,
                        "city": has_valid_city_field,
                    }
                    existing_validator = existing_validators.get(field)
                    if existing_validator is not None and not existing_validator(lead):
                        setattr(lead, field, sanitized_value)
                        continue
                    if field == "company" and lead.name and self._normalize(sanitized_value) == self._normalize(lead.name):
                        continue
                    if self._is_noisier_field_update(existing_value, sanitized_value):
                        continue
                    if len(sanitized_value) < len(existing_value):
                        continue
                setattr(lead, field, sanitized_value)
        if extracted_data.get("urgency"):
            lead.urgency = extracted_data["urgency"]

        if collecting_contact and explicit_lead is None:
            collection_anchor = self._contact_collection_anchor_message(conversation)
            self._backfill_contact_fields_from_recent_messages(
                lead,
                conversation,
                current_user_message,
                collection_anchor=collection_anchor,
                expected_field=expected_field_before_update,
            )
            self._apply_expected_field_answer(lead, expected_field_before_update, current_user_message)
        elif collecting_contact and explicit_lead is not None:
            self._apply_expected_field_answer(lead, expected_field_before_update, current_user_message)
        self._backfill_explicit_city_from_cycle(lead, conversation, current_user_message)
        self._enrich_lead_from_conversation(lead, conversation)
        if lead.name and lead.company and self._normalize(lead.company) == self._normalize(lead.name):
            lead.company = ""
        if lead.city and not has_valid_city_field(lead):
            lead.city = ""
        if lead.city and lead.name and self._normalize(lead.city) == self._normalize(lead.name):
            lead.city = ""
        if lead.city and lead.company and self._normalize(lead.city) == self._normalize(lead.company):
            lead.city = ""
        if expected_field_before_update == "email" and current_user_message and self._explicitly_refused_email(current_user_message.content):
            lead.crm_reference = {**(lead.crm_reference or {}), "missing_email": True}
        lead.is_qualified = is_lead_ready_for_notification(lead)
        if self._is_pending_required_field_unanswered(expected_field_before_update, lead):
            lead.is_qualified = False
        
        self._enrich_lead_from_conversation(lead, conversation)

        print(f"DEBUG CAPTURE UPDATE: msg='{current_user_message.content if current_user_message else ''}', extracting={extracted_data}, expected={expected_field_before_update}, lead.name='{lead.name}', lead.company='{lead.company}'")

        self._persist_lead_state(lead, conversation, extracted_data)
        lead.save()

        update_fields = []
        if visitor_name_cleared:
            update_fields.append("visitor_name")
        if lead.name and not conversation.visitor_name:
            conversation.visitor_name = lead.name
            if "visitor_name" not in update_fields:
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

        was_already_notified = self._lead_was_notified(lead)
        if lead.is_qualified:
            try:
                LiviaCRMBridge().create_or_update_crm_lead(lead)
            except Exception as exc:  # pragma: no cover - defensive CRM bridge guard
                logger.warning("Lívia CRM bridge failed; lead kept locally. Error type: %s", exc.__class__.__name__)

        notification_sent_this_turn = bool(
            lead.is_qualified
            and self._lead_was_notified(lead)
            and not was_already_notified
        )
        lead.crm_reference = {
            **(lead.crm_reference or {}),
            "notification_sent_this_turn": notification_sent_this_turn,
        }
        if notification_sent_this_turn or lead.is_qualified:
            lead.save(update_fields=["crm_reference"])

        return lead

    def _seed_lead_contact_from_conversation(self, lead, conversation):
        if any(
            self._is_capture_cycle_locked(existing)
            for existing in conversation.lead_captures.order_by("-created_at", "-id")
        ):
            return
        if lead.name and not has_valid_name_field(lead):
            lead.name = ""
        if lead.city and not has_valid_city_field(lead):
            lead.city = ""

    def _conversation_was_notified(self, conversation):
        if self.get_open_lead_capture(conversation) is not None:
            return False
        for capture in LiviaLeadCapture.objects.filter(conversation_id=conversation.id):
            if (capture.crm_reference or {}).get("notification_sent_at"):
                return True
        return False

    def _lead_was_notified(self, lead):
        return bool((lead.crm_reference or {}).get("notification_sent_at"))

    def get_open_lead_capture(self, conversation):
        return self._get_active_lead_capture(conversation)

    def should_start_new_commercial_cycle(self, conversation, user_message, existing_capture=None):
        existing_capture = existing_capture or self.get_locked_lead_capture(conversation)
        if existing_capture is None or not self._is_capture_cycle_locked(existing_capture):
            return False
        normalized = self._normalize(user_message)
        if self.is_cycle_closing_message(normalized):
            return False
        if any(term in normalized for term in ("tambem", "também", "alem disso", "além disso", "mais uma coisa")):
            return False
        if is_clear_technical_issue(normalized):
            return False
        system_need = "sistema" in normalized and any(
            term in normalized
            for term in ("interessado", "interesse", "criar", "preciso", "quero", "marmoraria", "deposito", "depósito")
        )
        if system_need:
            return True
        if self.should_capture_post_qualified_update_for_conversation(user_message, conversation):
            return False
        return (
            is_lead_capture_intent(normalized)
            or is_web_system_project_text(normalized)
            or self._looks_like_problem_description(user_message)
            or system_need
        )

    def is_same_contact_cycle(self, existing_lead, new_contact_data):
        if existing_lead is None:
            return False
        normalized_name = self._normalize(new_contact_data.get("name", ""))
        normalized_existing_name = self._normalize(getattr(existing_lead, "name", ""))
        if normalized_name and normalized_existing_name and normalized_name != normalized_existing_name:
            return False
        phone = re.sub(r"\D", "", str(new_contact_data.get("phone", "")))
        existing_phone = re.sub(r"\D", "", str(getattr(existing_lead, "phone", "")))
        if phone and existing_phone and phone != existing_phone:
            return False
        email = self._normalize(new_contact_data.get("email", ""))
        existing_email = self._normalize(getattr(existing_lead, "email", ""))
        if email and existing_email and email != existing_email:
            return False
        return bool(normalized_name or phone or email)

    def is_cycle_closing_message(self, text):
        normalized = self._normalize(text)
        closing_terms = (
            "por hora e so",
            "por hora é só",
            "por enquanto e so",
            "por enquanto é só",
            "obrigado",
            "obrigada",
            "ate mais",
            "até mais",
            "valeu",
            "só isso",
            "so isso",
        )
        return any(term in normalized for term in closing_terms)

    def close_current_commercial_cycle(self, conversation):
        lead = self._latest_lead_capture(conversation)
        if lead is None:
            return None
        reference = dict(lead.crm_reference or {})
        reference["lead_state"] = LeadState.CLOSED
        reference["closed_by_user"] = True
        lead.crm_reference = reference
        lead.save(update_fields=["crm_reference"])
        return lead

    def is_new_commercial_cycle_message(self, message, conversation):
        return self.should_start_new_commercial_cycle(conversation, message)

    def _conversation_has_complete_contact(self, conversation):
        locked_lead = self.get_locked_lead_capture(conversation)
        if locked_lead is None:
            return False
        return is_lead_ready_for_notification(locked_lead)

    def _is_logistics_web_context(self, normalized_text):
        from .integrations import _is_logistics_web_context

        return _is_logistics_web_context(normalized_text)

    def _resolve_web_service_interest_label(self, normalized_text):
        if self._is_logistics_web_context(normalized_text):
            return "desenvolvimento de sistema logístico web com IA integrada"
        return "desenvolvimento de sistema web com IA integrada"

    def should_send_qualified_reply(self, lead):
        if getattr(lead, "pk", None):
            return bool(lead.is_qualified)
        return is_lead_ready_for_notification(lead)

    def build_lead_confirmation_reply(self, lead, *, notification_sent_this_turn=False):
        first_name = (lead.name or "").split()[0] if has_valid_name_field(lead) else ""
        summary = self._build_commercial_context_summary(lead)
        conversation_already_notified = self._conversation_was_notified(lead.conversation)

        if notification_sent_this_turn:
            greeting = f"Perfeito, {first_name}. " if first_name else "Perfeito. "
            return (
                f"{greeting}Vou encaminhar seu pedido para nossa equipe com este resumo: {summary}. "
                "Um especialista da Smart Control Brasil entrará em contato."
            )

        if lead.is_qualified and conversation_already_notified:
            return "Já temos seus dados registrados. Vou acrescentar essa informação ao atendimento."

        if lead.is_qualified:
            greeting = f"Perfeito, {first_name}. " if first_name else ""
            return f"{greeting}Recebi seus dados. Vou deixar registrado para análise da equipe."

        return self.build_progressive_lead_reply(lead)

    def build_existing_attendance_append_reply(self, lead=None):
        del lead
        return "Já temos seus dados registrados. Vou acrescentar essa informação ao atendimento."

    def build_progressive_lead_reply(self, lead):
        invalid_field = (lead.crm_reference or {}).get("invalid_contact_field")
        invalid_value = (lead.crm_reference or {}).get("invalid_contact_value")
        if invalid_field == "phone":
            return f"O telefone {invalid_value} parece incompleto ou fora do padrão brasileiro. Pode confirmar com DDD, por favor?"
        if invalid_field == "email":
            return f"O e-mail {invalid_value} parece estar fora do formato. Pode confirmar o endereço correto, por favor?"

        snapshot = self._current_state_snapshot(lead, conversation=lead.conversation)
        if snapshot.state == LeadState.DISCOVERY:
            from .discovery import build_consultative_discovery_reply

            messages = self._build_recent_messages(lead.conversation)
            last_user = (
                lead.conversation.messages.filter(role=LiviaMessage.Role.USER)
                .order_by("-created_at", "-id")
                .first()
            )
            normalized = self._normalize(last_user.content if last_user else "")
            return build_consultative_discovery_reply(normalized, messages)
        if snapshot.state == LeadState.COLLECT_NAME:
            return self._build_collect_name_reply(lead)
        if snapshot.state == LeadState.COLLECT_COMPANY:
            return f"Perfeito, {lead.name.split()[0]}. Agora preciso do nome da empresa, por favor."
        if snapshot.state == LeadState.COLLECT_CITY:
            return "Em qual cidade fica sua empresa?"
        if snapshot.state == LeadState.COLLECT_PHONE:
            return "Qual é o melhor telefone/WhatsApp para nossa equipe falar com você?"
        if snapshot.state == LeadState.COLLECT_EMAIL:
            return "Qual e-mail podemos usar para formalizar o atendimento?"

        missing_field = snapshot.next_field or first_missing_required_field(lead)
        return self._ask_for_field(missing_field, lead)

    def _ask_for_field(self, field, lead):
        if field == "name":
            return self._build_collect_name_reply(lead)
        if field == "company":
            first_name = (lead.name or "").split()[0] or ""
            if first_name:
                return f"Perfeito, {first_name}. Agora preciso do nome da empresa, por favor."
            return "Agora preciso do nome da empresa, por favor."
        if field == "city":
            return "Em qual cidade fica sua empresa?"
        if field == "phone":
            return "Qual é o melhor telefone/WhatsApp para nossa equipe falar com você?"
        if field == "email":
            return "Qual e-mail podemos usar para formalizar o atendimento?"
        return self._build_collect_name_reply(lead)

    def _build_collect_name_reply(self, lead):
        from .discovery import build_digital_product_interest_summary

        corpus = self._normalize(self._technical_corpus(lead))
        digital_summary = build_digital_product_interest_summary(corpus)
        if digital_summary:
            return (
                f"Entendi. Temos um bom ponto de partida para {digital_summary}. "
                "Para nossa equipe avaliar melhor, posso registrar seu atendimento? Como posso te chamar?"
            )
        context_ack = self._technical_context_acknowledgment(lead)
        if context_ack:
            return f"{context_ack} Para encaminhar corretamente, como posso te chamar?"
        return "Para encaminhar seu pedido, como posso te chamar?"

    def _technical_context_acknowledgment(self, lead):
        summary = self._build_technical_service_summary(lead)
        if not summary:
            return ""
        detail = summary.removeprefix("Solicitação de atendimento técnico para ").rstrip(".")
        if not detail:
            return ""
        return f"Claro. Pelo que entendi, é {detail}."

    def build_qualified_lead_reply(self, lead):
        notification_sent_this_turn = bool((lead.crm_reference or {}).get("notification_sent_this_turn"))
        return self.build_lead_confirmation_reply(
            lead,
            notification_sent_this_turn=notification_sent_this_turn,
        )

    def _backfill_explicit_city_from_cycle(self, lead, conversation, current_user_message):
        del current_user_message
        if has_valid_city_field(lead):
            return
        messages = conversation.messages.filter(role=LiviaMessage.Role.USER).order_by("created_at", "id")
        for message in messages:
            candidate = self._extract_explicit_city(message.content or "")
            if candidate:
                lead.city = candidate
                return

    def _enrich_lead_from_conversation(self, lead, conversation):
        technical_messages = []
        for message in self._cycle_user_messages(lead, conversation):
            content = (message.content or "").strip()
            if not content:
                continue
            sanitized = self._sanitize_message_for_notes(content)
            if sanitized:
                technical_messages.append(sanitized)

        selected_messages = technical_messages
        corpus = " ".join(selected_messages)
        normalized = self._normalize(corpus)

        normalized_notes = self._normalize(lead.notes or "")
        if (not lead.notes or normalized_notes in INVALID_GENERIC_VALUES) and corpus:
            lead.notes = corpus

        technical_reference = {
            **(lead.crm_reference or {}),
            "technical_history": selected_messages,
        }
        web_summary = web_system_interest_summary(normalized)
        if web_summary:
            technical_reference["category"] = "sistemas_web_ia"
        context = None if web_summary else (extract_technical_context(corpus) if corpus else None)
        if context and (context.equipment or context.symptom or context.stopped or context.intent):
            technical_reference["technical_context"] = {
                "equipment": context.equipment,
                "brand": context.brand,
                "symptom": context.symptom,
                "intent": context.intent,
                "stopped": context.stopped,
            }
        lead.crm_reference = technical_reference

        city = lead.city if has_valid_city_field(lead) else ""
        structured_summary = "" if web_summary else build_technical_service_summary(raw_corpus=corpus, city=city)
        commercial_summary = self._build_commercial_fallback_summary(lead)
        if web_summary:
            lead.notes = web_summary
        elif self._should_use_commercial_notes(corpus, commercial_summary):
            lead.notes = commercial_summary
        elif structured_summary:
            lead.notes = structured_summary
        elif selected_messages:
            lead.notes = " | ".join(dict.fromkeys(selected_messages))[:4000]
        elif is_lead_capture_intent(normalized):
            lead.notes = commercial_summary

        if web_summary:
            lead.service_interest = self._resolve_web_service_interest_label(normalized)
        elif any(term in normalized for term in ("duno", "dune", "hygibot")):
            lead.service_interest = "Duno - robô de limpeza"
        elif not lead.service_interest or (
            self._is_logistics_web_context(normalized)
            and "consultoria" in self._normalize(lead.service_interest or "")
        ):
            detected = self._detect_service_interest(normalized)
            if self._is_logistics_web_context(normalized):
                lead.service_interest = self._resolve_web_service_interest_label(normalized)
            elif detected and "consultoria" not in self._normalize(detected):
                lead.service_interest = detected

    def _build_commercial_context_summary(self, lead):
        corpus = self._technical_corpus(lead)
        commercial_summary = self._build_commercial_fallback_summary(lead)
        if web_system_interest_summary(self._normalize(corpus)):
            return commercial_summary
        if self._should_use_commercial_notes(corpus, commercial_summary):
            return commercial_summary
        technical_summary = self._build_technical_service_summary(lead)
        if technical_summary:
            return technical_summary
        return commercial_summary

    def _build_commercial_fallback_summary(self, lead):
        normalized = self._normalize(self._technical_corpus(lead))
        web_summary = web_system_interest_summary(normalized)
        if web_summary:
            return web_summary
        if (lead.service_interest or "").lower() == "desenvolvimento de sistema web com ia integrada":
            return "Solicitação de orçamento para desenvolvimento de sistema web com IA integrada."
        product = "robô Duno" if any(
            term in normalized for term in ("duno", "dune", "hygibot")
        ) or ("robô" in normalized or "robo" in normalized) and "supermercado" in normalized else "solução solicitada"
        application = " para limpeza noturna" if "limpeza" in normalized and "noturn" in normalized else " para limpeza" if "limpeza" in normalized else ""
        environment = " em supermercado" if "supermercado" in normalized else ""
        area_match = re.search(r"(\d{1,3}(?:[.]\d{3})+|\d+)\s*m(?:²|2)", self._technical_corpus(lead), re.IGNORECASE)
        area = f" de aproximadamente {area_match.group(1)} m²" if area_match else ""
        infrastructure = ", sem infraestrutura de automação atual" if any(term in normalized for term in ("sem infraestrutura", "nao possui infraestrutura", "não possui infraestrutura")) else ""
        city = f", em {lead.city}" if has_valid_city_field(lead) else ""
        if product != "solução solicitada" or application or environment or area or infrastructure or city:
            return f"{product}{application}{environment}{area}{infrastructure}{city}"
        return "solicitação comercial registrada"

    def _technical_corpus(self, lead):
        return technical_corpus_from_lead(lead)

    def _should_use_commercial_notes(self, corpus, commercial_summary):
        normalized = self._normalize(corpus)
        if not commercial_summary or commercial_summary == "solicitação comercial registrada":
            return False
        return any(term in normalized for term in ("supermercado", "duno", "dune", "hygibot")) and "limpeza" in normalized

    def _build_technical_service_summary(self, lead):
        corpus = self._technical_corpus(lead)
        if lead.service_interest:
            corpus = f"{corpus} {lead.service_interest}"
        city = lead.city if has_valid_city_field(lead) else ""
        return build_technical_service_summary(raw_corpus=corpus, city=city)

    def _extract_relaxed_phone(self, text):
        value = str(text or "").strip()
        if re.fullmatch(r"[+()\d .-]+", value) and 8 <= len(re.sub(r"\D", "", value)) <= 15:
            return value
        return ""

    def _requested_lead_field_from_assistant(self, text):
        normalized = self._normalize(text)
        prompts = (
            ("name", ("como posso te chamar", "qual é o seu nome", "qual e o seu nome")),
            ("company", self.COMPANY_ASSISTANT_MARKERS),
            ("phone", ("telefone/whatsapp", "qual é o melhor telefone", "qual e o melhor telefone")),
            ("email", (
                "qual é o melhor e-mail",
                "qual e o melhor e-mail",
                "qual é o seu e-mail",
                "qual e o seu e-mail",
                "qual e-mail podemos usar para formalizar o atendimento",
            )),
            ("city", ("em qual cidade", "qual cidade você está")),
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
        normalized = self._normalize(value)
        if normalized in INVALID_GENERIC_VALUES:
            return ""
        if (
            self._looks_like_personal_only_input(value)
            and not self._looks_like_problem_description(value)
            and not self._is_technical_note_message(normalized)
        ):
            return ""
        if any(snippet in normalized for snippet in INVALID_COMPANY_OR_CITY_SNIPPETS):
            if not self._is_technical_note_message(normalized):
                return ""
        if not self._looks_like_problem_description(value) and not self._is_technical_note_message(normalized) and not is_web_system_project_text(normalized) and not is_lead_capture_intent(normalized):
            return ""
        sanitized = re.sub(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", "", value, flags=re.IGNORECASE)
        sanitized = re.sub(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}", "", sanitized)
        sanitized = re.sub(r"\b(?:meu nome é|me chamo|nome)\s+[A-Za-zÀ-ÿ ]{2,80}", "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"\b(?:sou da|empresa|trabalho na)\s+[A-Za-z0-9À-ÿ .&-]{2,100}", "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"\s+", " ", sanitized).strip(" ,.-")
        return sanitized[:300]

    def _is_technical_note_message(self, normalized):
        technical_terms = (
            "camara climatica",
            "câmara climática",
            "camara frigorifica",
            "câmara frigorífica",
            "ar condicionado",
            "ar-condicionado",
            "erro e2",
            "choque termico",
            "choque térmico",
            "weiss",
            "votsch",
            "vötsch",
            "duno",
            "robo",
            "robô",
            "supermercado",
            "limpeza",
            "infraestrutura",
            "noturno",
            "noturna",
            "periodo noturno",
            "período noturno",
            "placa",
            "m²",
            "m2",
            "nao gela",
            "não gela",
            "low pressure",
            "painel apagou",
            "painel parou",
            "apagou o painel",
            "maquina parou",
            "máquina parou",
            "gelo no ventilador",
            "acumulo de gelo",
            "acúmulo de gelo",
            "disjuntor",
            "avaliacao",
            "avaliação",
            "contrato",
            "problema",
            "parou",
            "equipamennto",
            "equipamento",
        )
        return any(term in normalized for term in technical_terms)

    def _cycle_user_messages(self, lead, conversation, current_user_message=None):
        start_id = (lead.crm_reference or {}).get("capture_start_message_id")
        messages = list(
            conversation.messages.filter(role=LiviaMessage.Role.USER).order_by("created_at", "id")
        )
        if start_id:
            messages = [message for message in messages if message.id >= start_id]
        if current_user_message:
            messages = [message for message in messages if message.id <= current_user_message.id]
        return messages

    def _contact_collection_anchor_message(self, conversation):
        for message in conversation.messages.filter(role=LiviaMessage.Role.ASSISTANT).order_by("-created_at", "-id"):
            if self._requested_lead_field_from_assistant(message.content):
                return message
        return None

    def _is_discovery_context_message(self, text):
        normalized = self._normalize(text)
        discovery_terms = (
            "cadastro",
            "clientes",
            "celular",
            "tablet",
            "computador",
            "artesanato",
            "transformar",
            "foto",
            "fotos",
            "orcamento",
            "orçamento",
            "sistema web",
            "aplicativo",
            "app ",
        )
        if any(term in normalized for term in discovery_terms):
            return True
        return self._looks_like_problem_description(text) or is_web_system_project_text(normalized)

    def _backfill_contact_fields_from_recent_messages(
        self,
        lead,
        conversation,
        current_user_message,
        collection_anchor=None,
        expected_field="",
    ):
        messages = self._cycle_user_messages(lead, conversation, current_user_message=current_user_message)
        if not messages:
            return

        if collection_anchor is not None:
            messages = [message for message in messages if message.id > collection_anchor.id]
        recent_texts = [message.content.strip() for message in messages[-8:] if message.content.strip()]

        if not lead.name:
            single_word_candidates = [
                text
                for text in reversed(recent_texts)
                if len(text.split()) == 1
                and _is_valid_name(text)
                and not self._is_technical_note_message(self._normalize(text))
                and not self._is_discovery_context_message(text)
            ]
            if single_word_candidates:
                lead.name = single_word_candidates[0]
            else:
                multi_word_candidates = [
                    text
                    for text in reversed(recent_texts)
                    if self._extract_conversational_field_value(text, "name")
                    and self._looks_like_personal_only_input(text)
                    and len(text.split()) >= 2
                    and not self._looks_like_problem_description(text)
                    and not self._is_discovery_context_message(text)
                    and self._normalize(text) not in {"sim", "nao", "não"}
                ]
                if multi_word_candidates:
                    lead.name = multi_word_candidates[0]

        if not lead.company and expected_field in {"company", "city", "phone", "email"}:
            for text in reversed(recent_texts):
                normalized_text = self._normalize(text)
                if self._is_discovery_context_message(text):
                    continue
                if any(
                    marker in normalized_text
                    for marker in ("meu nome", "me chamo", "sou da", "telefone", "whatsapp", "email", "e-mail")
                ):
                    continue
                candidate = strip_repetition_noise(self._extract_conversational_field_value(text, "company"))
                if not candidate:
                    raw = strip_repetition_noise(str(text).strip())
                    if (
                        raw
                        and _is_valid_company_or_city(raw)
                        and not self._looks_like_problem_description(raw)
                        and not self._is_technical_note_message(self._normalize(raw))
                        and len(raw.split()) <= 5
                        and not (_is_valid_name(raw) and len(raw.split()) == 1)
                        and not (
                            self._is_valid_city_candidate(raw)
                            and len(raw.split()) == 1
                        )
                    ):
                        candidate = raw
                if not candidate or not _is_valid_company_or_city(candidate):
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

    def _apply_expected_field_answer(self, lead, expected_field, current_user_message):
        if not expected_field or current_user_message is None:
            return
        text = str(current_user_message.content or "").strip()
        if not text:
            return
        if self._is_discovery_context_message(text):
            return
        if expected_field == "company":
            stripped_company = strip_repetition_noise(text)
            if (
                self._is_valid_city_candidate(stripped_company)
                and len(stripped_company.split()) == 1
                and not any(
                    marker in self._normalize(text)
                    for marker in ("empresa", "sou da", "trabalho na", "da empresa")
                )
            ):
                return
        value = ""
        if expected_field in {"name", "company", "city"}:
            value = self._extract_conversational_field_value(text, expected_field)
            if expected_field == "company" and not value:
                value = self._extract_explicit_company(text) or (
                    stripped_company
                    if stripped_company and _is_valid_company_or_city(stripped_company)
                    else ""
                )
        elif expected_field == "phone":
            value = self._extract_relaxed_phone(text) or ""
            if not value:
                match = re.search(r"(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[-\s]?\d{4}", text)
                value = match.group(0).strip() if match else ""
        elif expected_field == "email":
            match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE)
            value = match.group(0).strip() if match else ""
        sanitized_value = self._sanitize_lead_field_before_save(expected_field, value)
        if not sanitized_value:
            if expected_field in {"phone", "email"} and self._looks_like_invalid_contact_attempt(text, expected_field):
                lead.crm_reference = {
                    **(lead.crm_reference or {}),
                    "invalid_contact_field": expected_field,
                    "invalid_contact_value": text[:120],
                }
            return
        if expected_field in {"phone", "email"}:
            reference = dict(lead.crm_reference or {})
            reference.pop("invalid_contact_field", None)
            reference.pop("invalid_contact_value", None)
            lead.crm_reference = reference
        if expected_field == "company" and lead.name and self._normalize(sanitized_value) == self._normalize(lead.name):
            return
        setattr(lead, expected_field, sanitized_value)

    def _mentions_name_correction(self, text):
        normalized = self._normalize(text)
        markers = (
            "nao sou",
            "não sou",
            "nao me chamo",
            "não me chamo",
            "ainda nao te falei meu nome",
            "ainda não te falei meu nome",
            "nao te falei meu nome",
            "não te falei meu nome",
            "nao falei meu nome",
            "não falei meu nome",
        )
        return any(marker in normalized for marker in markers)

    def _message_answers_expected_field(self, text, expected_field):
        normalized = self._normalize(text)
        stripped = strip_repetition_noise(str(text or "").strip())
        if not stripped or not expected_field:
            return False
        if expected_field == "phone":
            digits = re.sub(r"\D", "", stripped)
            if len(digits) in {12, 13} and digits.startswith("55"):
                digits = digits[2:]
            return len(digits) in {10, 11}
        if expected_field == "email":
            if re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE):
                return True
            return any(term in normalized for term in ("email", "e-mail"))
        if expected_field == "name":
            explicit_name = self._extract_explicit_name(text)
            if explicit_name:
                return True
            return len(stripped.split()) <= 2 and _is_valid_name(stripped)
        if expected_field == "company":
            if any(
                marker in normalized
                for marker in ("empresa", "sou da", "trabalho na", "da empresa")
            ):
                return True
            if len(stripped.split()) >= 2:
                return _is_valid_company_or_city(stripped)
            if self._is_valid_city_candidate(stripped):
                return False
            return _is_valid_company_or_city(stripped)
        if expected_field == "city":
            return bool(self._extract_conversational_field_value(text, "city") or self._extract_explicit_city(text))
        return False

    def _extract_explicit_city(self, text):
        raw = str(text or "").strip()
        case_insensitive_patterns = (
            r"\bminha cidade é\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]{1,80})",
            r"\bsou de\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]{1,80})",
            r"\bestou em\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]{1,80})",
            r"\bfico em\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]{1,80})",
            r"\ba empresa fica em\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]{1,80})",
            r"\bcidade\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]{1,80})",
        )
        for pattern in case_insensitive_patterns:
            match = re.search(pattern, raw, re.IGNORECASE)
            if not match:
                continue
            candidate = match.group(1).strip(" .,-")
            if self._is_valid_city_candidate(candidate):
                return candidate[:120]
        match = re.search(
            r"(?:^|[\s,.])em\s+([A-ZÀ-ÿ][A-Za-zÀ-ÿáéíóúâêîôûãõç .'-]{2,80})",
            raw,
        )
        if match:
            candidate = match.group(1).strip(" .,-")
            if self._is_valid_city_candidate(candidate):
                return candidate[:120]
        return ""

    def _is_valid_city_candidate(self, value):
        cleaned = strip_repetition_noise(str(value or "").strip(" .,-"))
        normalized = self._normalize(cleaned)
        if not cleaned or normalized in self.INVALID_CITY_VALUES or normalized in self.INVALID_COMPANY_OR_CITY_VALUES:
            return False
        if len(cleaned.split()) > 5:
            return False
        if any(snippet in normalized for snippet in INVALID_COMPANY_OR_CITY_SNIPPETS):
            return False
        if self._looks_like_problem_description(cleaned) or self._is_technical_note_message(normalized):
            return False
        if any(
            term in normalized
            for term in (
                "sistema",
                "marmoraria",
                "deposito",
                "depósito",
                "caderno",
                "anotacao",
                "anotação",
                "planilha",
                "excel",
                "celular",
                "tablet",
                "computador",
                "cliente",
                "clientes",
                "estoque",
                "vendas",
                "pedido",
                "pedidos",
                "foto",
                "arte",
            )
        ):
            return False
        if re.search(r"\b(?:faço|faco|acho|tenho|preciso|quero|uso|usamos|controlar|vender|captar|organizar|transformar)\b", normalized):
            return False
        return _is_valid_company_or_city(cleaned)

    def _looks_like_invalid_contact_attempt(self, text, field):
        value = str(text or "").strip()
        if field == "phone":
            digits = re.sub(r"\D", "", value)
            if len(digits) in {12, 13} and digits.startswith("55"):
                digits = digits[2:]
            return bool(digits) and len(digits) not in {10, 11}
        if field == "email":
            return "@" in value and not _is_valid_email(value)
        return False

    def _sanitize_lead_field_before_save(self, field, value):
        if field in {"name", "company", "city"}:
            value = strip_repetition_noise(value)
        validators = {
            "name": _is_valid_name,
            "company": _is_valid_company_or_city,
            "city": self._is_valid_city_candidate,
            "phone": _is_valid_phone,
            "email": _is_valid_email,
        }
        validator = validators.get(field)
        if validator is None:
            return value
        return value if validator(value) else ""

    def _is_noisier_field_update(self, existing_value, new_value):
        existing_clean = strip_repetition_noise(existing_value)
        new_clean = strip_repetition_noise(new_value)
        if self._normalize(existing_clean) == self._normalize(new_clean):
            return len(new_value) > len(existing_value)
        return False

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

    def _is_web_system_capability_question(self, normalized):
        if not is_web_system_project_text(normalized):
            return False
        return any(
            term in normalized
            for term in (
                "voces desenvolvem",
                "vocês desenvolvem",
                "desenvolvem sistemas",
                "desenvolvem sistema",
                "fazem sistema",
                "fazem sistemas",
                "vocês fazem",
                "voces fazem",
            )
        )

    def _looks_like_problem_description(self, text):
        normalized = self._normalize(text)
        return any(
            term in normalized
            for term in (
                "problema",
                "falha",
                "falhas",
                "parada",
                "paradas",
                "apagou",
                "low pressure",
                "choque",
                "erro e2",
                "curto",
                "queimado",
            )
        )

    def is_new_technical_cycle_message(self, text):
        normalized = self._normalize(text)
        if not normalized:
            return False
        if (
            self.should_capture_post_qualified_update(text)
            and not self._looks_like_problem_description(text)
            and not self._is_technical_note_message(normalized)
        ):
            return False
        if is_clear_technical_issue(normalized):
            return True
        if self._is_technical_note_message(normalized):
            return True
        if self._looks_like_problem_description(text):
            return True
        new_cycle_markers = (
            "estou com problema",
            "tenho problema",
            "minha maquina parou",
            "minha máquina parou",
            "erro e2",
            "disjuntor caindo",
            "disjuntor cai",
            "nao gela",
            "não gela",
            "outro equipamento",
            "manutencao em outro",
            "manutenção em outro",
        )
        return any(marker in normalized for marker in new_cycle_markers)

    def _is_contact_field_collection_phase(self, conversation):
        lead = self._get_active_lead_capture(conversation)
        if lead is None or lead.is_qualified or self._is_capture_cycle_locked(lead):
            return False
        return bool(first_missing_required_field(lead))

    def is_lead_collection_active(self, conversation):
        if self.needs_consultative_discovery_for_conversation(conversation):
            return False
        lead = self._get_active_lead_capture(conversation)
        if lead is None:
            return bool(self._expected_lead_field(conversation))
        if lead is not None and not lead.is_qualified:
            missing = first_missing_required_field(lead)
            if not missing:
                return False
            last_assistant = (
                conversation.messages.filter(role=LiviaMessage.Role.ASSISTANT)
                .order_by("-created_at", "-id")
                .first()
            )
            if last_assistant and self._requested_lead_field_from_assistant(last_assistant.content) == missing:
                return True
            last_user = (
                conversation.messages.filter(role=LiviaMessage.Role.USER)
                .order_by("-created_at", "-id")
                .first()
            )
            if last_user and self._is_contact_collection_reply(last_user.content, missing):
                return True
            return False
        return bool(self._expected_lead_field(conversation))

    def _expected_lead_field(self, conversation):
        if conversation is None:
            return ""
        lead = self._get_active_lead_capture(conversation)
        if lead is not None and not lead.is_qualified:
            missing = first_missing_required_field(lead)
            if missing:
                return missing
        if lead is not None:
            raw_state = (lead.crm_reference or {}).get("lead_state", "")
            if normalize_state(raw_state) in {LeadState.QUALIFIED, LeadState.CLOSED}:
                return ""
        if lead is not None and (lead.is_qualified or self._is_capture_cycle_locked(lead)):
            return ""
        last_assistant = conversation.messages.filter(role=LiviaMessage.Role.ASSISTANT).order_by("-created_at", "-id").first()
        if last_assistant is None:
            return ""
        normalized = self._normalize(last_assistant.content)
        prompts = (
            ("name", ("como posso te chamar", "qual é o seu nome", "qual e o seu nome", "informe seu nome", "informar seu nome", "me diga seu nome")),
            ("company", self.COMPANY_ASSISTANT_MARKERS),
            ("phone", ("qual é o melhor telefone", "qual e o melhor telefone", "telefone/whatsapp")),
            ("email", (
                "qual é o melhor e-mail",
                "qual e o melhor e-mail",
                "qual é o seu e-mail",
                "qual e o seu e-mail",
                "qual e-mail podemos usar para formalizar o atendimento",
            )),
            ("city", ("em qual cidade", "qual cidade você está")),
        )
        for field, markers in prompts:
            if any(marker in normalized for marker in markers):
                return field
        return ""

    def _extract_conversational_field_value(self, text, expected_field):
        value = strip_repetition_noise(str(text or "").strip(" .,-"))
        if expected_field not in {"name", "company", "city"} or not value or len(value) > 180:
            return ""
        if re.search(r"[@\d]", value) or "," in value or "?" in value:
            return ""
        normalized = self._normalize(value)
        if expected_field == "name":
            value = re.sub(r"^(?:meu nome é|meu nome|nome)\s+", "", value, flags=re.IGNORECASE).strip(" .,-")
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
            if any(snippet in normalized for snippet in INVALID_NAME_SNIPPETS):
                return ""
            if self._is_technical_note_message(normalized):
                return ""
            if len(value.split()) > 4:
                return ""
        if expected_field == "company":
            value = re.sub(r"^(?:empresa|sou da|da)\s+", "", value, flags=re.IGNORECASE).strip(" .,-")
            normalized = self._normalize(value)
            if normalized in {"sim", "nao", "não"}:
                return ""
            if normalized in self.INVALID_COMPANY_OR_CITY_VALUES:
                return ""
            if any(snippet in normalized for snippet in INVALID_COMPANY_OR_CITY_SNIPPETS):
                return ""
            if any(term in normalized for term in ("meu nome", "me chamo", "nome", "preciso", "equipamento", "automacao", "automação")):
                return ""
            if len(value.split()) > 5:
                return ""
        if expected_field == "city":
            value = re.sub(r"^(?:cidade|estou em|sou de|fico em|em)\s+", "", value, flags=re.IGNORECASE).strip(" .,-")
            normalized = self._normalize(value)
            if not self._is_valid_city_candidate(value):
                return ""
        if not value:
            return ""
        if not re.fullmatch(r"[A-Za-zÀ-ÿ][A-Za-z0-9À-ÿ .&/'-]{1,179}", value):
            return ""
        if expected_field == "company" and self._looks_like_problem_description(value) and len(value.split()) > 6:
            return ""
        return value

    def _extract_explicit_name(self, text):
        raw = str(text or "").strip()
        match = re.search(r"(?:meu nome é|me chamo|sou o|sou a)\s+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .'-]{1,80})", raw, re.IGNORECASE)
        if not match:
            return ""
        candidate = match.group(1).strip(" .,-")
        if len(candidate.split()) > 4:
            return ""
        if self._looks_like_problem_description(candidate):
            return ""
        return candidate[:150]

    def _extract_explicit_company(self, text):
        raw = str(text or "").strip()
        empresa_match = re.search(
            r"\b(empresa)\s+([A-Za-z0-9À-ÿ][A-Za-z0-9À-ÿ .&/'-]{1,100})",
            raw,
            re.IGNORECASE,
        )
        if empresa_match:
            prefix = empresa_match.group(1)
            suffix = empresa_match.group(2).strip(" .,-")
            candidate = f"Empresa {suffix}" if prefix[:1].isupper() else suffix
        else:
            match = re.search(
                r"(?:trabalho na|sou da)\s+([A-Za-z0-9À-ÿ][A-Za-z0-9À-ÿ .&/'-]{1,100})",
                raw,
                re.IGNORECASE,
            )
            if not match:
                return ""
            candidate = match.group(1).strip(" .,-")
        normalized = self._normalize(candidate)
        if normalized in self.INVALID_COMPANY_OR_CITY_VALUES:
            return ""
        if any(
            marker in normalized
            for marker in ("quero contato", "preciso de atendimento", "falar com especialista", "nao gela", "não gela", "low pressure")
        ):
            return ""
        if len(candidate.split()) > 5:
            return ""
        if self._looks_like_problem_description(candidate):
            return ""
        return candidate[:180]

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
            if 1 <= len(words) <= 3 and self._is_valid_city_candidate(part):
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
        return bool(lead.is_qualified and reference.get("notification_sent_at"))

    def _is_lead_cycle_locked(self, conversation):
        latest = self._latest_lead_capture(conversation)
        if latest is None:
            return False
        return self._is_capture_cycle_locked(latest)

    def _get_active_lead_capture(self, conversation, extracted_data=None):
        del extracted_data
        for lead in conversation.lead_captures.order_by("-created_at", "-id"):
            if self._is_capture_cycle_locked(lead):
                continue
            if lead.is_qualified:
                continue
            return lead
        return None

    def _has_meaningful_lead_update(self, extracted_data):
        if any((extracted_data.get(field) or "").strip() for field in ("name", "email", "phone", "company", "city", "service_interest")):
            return True
        notes = (extracted_data.get("notes") or "").strip()
        return bool(notes and self._looks_like_problem_description(notes))

    def _is_pending_required_field_unanswered(self, expected_field, lead):
        if not expected_field:
            return False
        field_validators = {
            "name": has_valid_name_field,
            "company": has_valid_company_field,
            "city": has_valid_city_field,
            "phone": has_valid_phone_field,
            "email": has_valid_email_field,
        }
        validator = field_validators.get(expected_field)
        if validator is None:
            return False
        return not validator(lead)

    def _explicitly_refused_email(self, text):
        normalized = self._normalize(text)
        refusal_markers = (
            "nao tenho email",
            "não tenho email",
            "nao tenho e-mail",
            "não tenho e-mail",
            "prefiro nao informar email",
            "prefiro não informar email",
            "sem email",
            "sem e-mail",
        )
        return any(marker in normalized for marker in refusal_markers)

    def _is_city_skippable(self, lead, conversation):
        del lead, conversation
        return False

    def _current_state_snapshot(self, lead, conversation=None):
        target_conversation = conversation or lead.conversation
        raw_state = (lead.crm_reference or {}).get("lead_state", "")
        collecting_states = {
            LeadState.COLLECT_NAME,
            LeadState.COLLECT_COMPANY,
            LeadState.COLLECT_CITY,
            LeadState.COLLECT_PHONE,
            LeadState.COLLECT_EMAIL,
        }
        has_collection_data = any(
            validator(lead)
            for validator in (
                has_valid_name_field,
                has_valid_company_field,
                has_valid_phone_field,
                has_valid_email_field,
                has_valid_city_field,
            )
        )
        if (
            self.needs_consultative_discovery_for_conversation(target_conversation)
            and raw_state not in collecting_states
            and not has_collection_data
        ):
            return LeadStateSnapshot(state=LeadState.DISCOVERY, next_field="", is_terminal=False)
        return resolve_state(
            has_intent=True,
            has_name=has_valid_name_field(lead),
            has_company=has_valid_company_field(lead),
            has_city=has_valid_city_field(lead),
            has_phone=has_valid_phone_field(lead),
            has_email=has_valid_email_field(lead),
            city_skippable=self._is_city_skippable(lead, conversation or lead.conversation),
            locked=self._is_capture_cycle_locked(lead),
        )

    def _persist_lead_state(self, lead, conversation, extracted_data):
        snapshot = self._current_state_snapshot(lead, conversation=conversation)
        updated_reference = dict(lead.crm_reference or {})
        updated_reference["lead_state"] = snapshot.state
        if extracted_data.get("product_hint"):
            updated_reference["product_hint"] = extracted_data["product_hint"]
        lead.crm_reference = updated_reference

    def get_locked_lead_capture(self, conversation):
        for lead in conversation.lead_captures.order_by("-created_at", "-id"):
            if self._is_capture_cycle_locked(lead):
                return lead
        return None

    def _extracted_has_valid_post_qualified_contact(self, extracted):
        from types import SimpleNamespace

        if has_valid_email_field(SimpleNamespace(email=extracted.get("email"))):
            return True
        if has_valid_city_field(SimpleNamespace(city=extracted.get("city"))):
            return True
        return False

    def should_capture_post_qualified_update(self, text):
        extracted = self.extract_lead_data(text)
        if self._extracted_has_valid_post_qualified_contact(extracted):
            return True
        normalized = self._normalize(text)
        if any(term in normalized for term in ("email", "e-mail", "cidade")) and any(
            term in normalized for term in ("quer", "posso", "informar", "passar", "saber", "qual")
        ):
            return True
        return False

    def should_capture_post_qualified_update_for_conversation(self, text, conversation):
        extracted = self.extract_lead_data(text)
        if self._extracted_has_valid_post_qualified_contact(extracted):
            return True
        normalized = self._normalize(text)
        if "cidade" in normalized and any(
            term in normalized for term in ("quer", "posso", "informar", "passar", "saber", "qual")
        ):
            return True
        if any(term in normalized for term in ("email", "e-mail")) and any(
            term in normalized for term in ("quer", "posso", "informar", "passar")
        ):
            return True
        expected = self._post_qualified_expected_field(conversation)
        if expected == "email":
            return bool(re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text or "", re.IGNORECASE))
        if expected == "city":
            return bool(self._extract_conversational_field_value(text, "city"))
        return False

    def apply_post_qualified_expected_field(self, extracted_data, text, conversation):
        expected = self._post_qualified_expected_field(conversation)
        updated = dict(extracted_data or {})
        if expected == "email" and not (updated.get("email") or "").strip():
            match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text or "", re.IGNORECASE)
            if match:
                updated["email"] = match.group(0).strip()
        if expected == "city" and not (updated.get("city") or "").strip():
            city_value = self._extract_conversational_field_value(text, "city")
            if city_value:
                updated["city"] = city_value
        return updated

    def _post_qualified_expected_field(self, conversation):
        if conversation is None:
            return ""
        last_assistant = (
            conversation.messages.filter(role=LiviaMessage.Role.ASSISTANT)
            .order_by("-created_at", "-id")
            .first()
        )
        if last_assistant is None:
            return ""
        normalized = self._normalize(last_assistant.content)
        if "informar" in normalized and ("e-mail" in normalized or "email" in normalized):
            return "email"
        if "informar a cidade" in normalized or ("cidade" in normalized and "adiciono ao atendimento" in normalized):
            return "city"
        return ""

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
                "eletrônica",
                "eletronica",
                "m²",
                "m2",
                "duno",
                "noturn",
                "noturno",
                "período noturno",
                "periodo noturno",
            "iot",
            "retrofit",
            "falha",
            "parada",
            "painel",
            "apagou",
            "low pressure",
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
            "cidade",
        )
        if any(marker in normalized for marker in continuation_markers):
            return True
        if self.is_new_technical_cycle_message(text):
            return False
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
