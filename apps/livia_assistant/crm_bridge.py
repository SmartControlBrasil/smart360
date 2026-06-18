import logging
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.utils import timezone

from .conversation_summary import build_lead_notification_body
from .models import LiviaHandoffRequest, LiviaLeadCapture
from .qualification import is_lead_ready_for_notification

logger = logging.getLogger(__name__)


class LiviaCRMBridge:
    def can_integrate(self) -> bool:
        try:
            self._growth_models()
            self._growth_services()
        except ImportError:
            return False
        return True

    @transaction.atomic
    def create_or_update_crm_lead(self, livia_lead) -> object | None:
        if not self.can_integrate() or not is_lead_ready_for_notification(livia_lead):
            return None

        Lead, LeadSource, LeadInteraction = self._growth_models()
        LeadService = self._growth_services()
        source = self._get_or_create_source(LeadSource)
        crm_lead = self._find_existing_lead(Lead, livia_lead, source)
        superseded_crm_lead = self._find_superseded_crm_lead(Lead, livia_lead, crm_lead, source)
        payload = self._payload_for_livia_lead(livia_lead, source)

        if crm_lead is None:
            crm_lead = LeadService.create_lead(user=None, validated_data=payload)
        else:
            merged_metadata = {**(crm_lead.metadata or {}), **payload.pop("metadata", {})}
            payload["metadata"] = merged_metadata
            crm_lead = LeadService.update_lead(lead=crm_lead, validated_data=payload, user=None)

        if superseded_crm_lead is not None:
            superseded_crm_lead.delete()

        previous_reference = dict(livia_lead.crm_reference or {})
        livia_lead.crm_lead_id = crm_lead.id
        livia_lead.crm_reference = {
            **previous_reference,
            "app": "growth_engine",
            "model": "Lead",
            "id": crm_lead.id,
            "public_id": str(crm_lead.public_id),
            "synced_at": timezone.now().isoformat(),
        }
        livia_lead.operational_status = LiviaLeadCapture.OperationalStatus.SENT_TO_CRM
        livia_lead.save(update_fields=["crm_lead_id", "crm_reference", "operational_status"])
        self._record_bridge_interaction(LeadInteraction, crm_lead, livia_lead)
        self._notify_team_if_needed(livia_lead=livia_lead, crm_lead=crm_lead)
        self._notify_n8n_if_needed(livia_lead=livia_lead, crm_lead=crm_lead)
        return crm_lead

    def create_followup_task(self, livia_lead) -> object | None:
        if not self.can_integrate():
            return None
        Lead, LeadSource, LeadInteraction = self._growth_models()
        source = self._get_or_create_source(LeadSource)
        crm_lead = self._find_existing_lead(Lead, livia_lead, source)
        if crm_lead is None and is_lead_ready_for_notification(livia_lead):
            crm_lead = self.create_or_update_crm_lead(livia_lead)
        if crm_lead is None:
            return None

        return LeadInteraction.objects.create(
            lead=crm_lead,
            interaction_type=LeadInteraction.InteractionType.NOTE,
            channel=LeadInteraction.Channel.WHATSAPP,
            summary=(
                "Follow-up comercial recomendado pela Lívia. "
                f"Interesse: {livia_lead.service_interest or 'não informado'}. "
                f"Urgência: {livia_lead.get_urgency_display()}."
            ),
        )

    def mark_contacted(self, livia_lead):
        if self.can_integrate():
            Lead, LeadSource, LeadInteraction = self._growth_models()
            source = self._get_or_create_source(LeadSource)
            crm_lead = self._find_existing_lead(Lead, livia_lead, source)
            if crm_lead:
                crm_lead.status = Lead.Status.CONTACTED
                crm_lead.save(update_fields=["status", "updated_at"])
                LeadInteraction.objects.create(
                    lead=crm_lead,
                    interaction_type=LeadInteraction.InteractionType.NOTE,
                    channel=LeadInteraction.Channel.WHATSAPP,
                    summary="Lead marcado como contatado a partir do painel da Lívia.",
                )
        livia_lead.operational_status = LiviaLeadCapture.OperationalStatus.CONTACTED
        livia_lead.save(update_fields=["operational_status"])
        return livia_lead

    def create_livia_handoff(self, livia_lead, reason="Lead comercial pediu continuidade humana pelo painel da Lívia."):
        handoff, _ = LiviaHandoffRequest.objects.get_or_create(
            conversation=livia_lead.conversation,
            status=LiviaHandoffRequest.Status.PENDING,
            defaults={"reason": reason},
        )
        return handoff

    def _find_existing_lead(self, Lead, livia_lead, source):
        if livia_lead.email:
            lead = Lead.objects.filter(email__iexact=livia_lead.email, source=source).first()
            if lead:
                return lead
        if livia_lead.crm_lead_id:
            lead = Lead.objects.filter(pk=livia_lead.crm_lead_id).first()
            if lead:
                return lead
        if livia_lead.phone:
            return (
                Lead.objects.filter(phone=livia_lead.phone, source=source).first()
                or Lead.objects.filter(whatsapp=livia_lead.phone, source=source).first()
            )
        return None

    def _find_superseded_crm_lead(self, Lead, livia_lead, crm_lead, source):
        if not livia_lead.email or not livia_lead.crm_lead_id or crm_lead is None:
            return None
        if livia_lead.crm_lead_id == crm_lead.id:
            return None
        return Lead.objects.filter(pk=livia_lead.crm_lead_id, source=source).first()

    def _get_or_create_source(self, LeadSource):
        source, _ = LeadSource.objects.get_or_create(
            name="Lívia Assistente",
            defaults={
                "source_type": LeadSource.SourceType.ORGANIC,
                "description": "Leads qualificados pela assistente virtual Lívia no site institucional.",
                "is_active": True,
            },
        )
        return source

    def _payload_for_livia_lead(self, livia_lead, source):
        company_name = livia_lead.company or livia_lead.name or "Lead Lívia"
        notes = "\n".join(
            part
            for part in [
                "Lead capturado pela Lívia Assistente.",
                f"Serviço de interesse: {livia_lead.service_interest}" if livia_lead.service_interest else "",
                f"Urgência: {livia_lead.get_urgency_display()}",
                livia_lead.notes,
            ]
            if part
        )
        return {
            "company_name": company_name[:180],
            "contact_name": livia_lead.name[:150],
            "email": livia_lead.email,
            "phone": livia_lead.phone[:30],
            "whatsapp": livia_lead.phone[:30],
            "city": livia_lead.city[:100],
            "source": source,
            "status": "qualified",
            "notes": notes,
            "metadata": {
                "source": "livia_assistant",
                "livia_lead_id": livia_lead.id,
                "livia_conversation_id": livia_lead.conversation_id,
                "service_interest": livia_lead.service_interest,
                "urgency": livia_lead.urgency,
            },
        }

    def _record_bridge_interaction(self, LeadInteraction, crm_lead, livia_lead):
        if LeadInteraction.objects.filter(
            lead=crm_lead,
            summary__icontains=f"Lead Lívia #{livia_lead.id}",
        ).exists():
            return None
        return LeadInteraction.objects.create(
            lead=crm_lead,
            interaction_type=LeadInteraction.InteractionType.NOTE,
            channel=LeadInteraction.Channel.WHATSAPP,
            summary=f"Lead Lívia #{livia_lead.id} sincronizado com o Growth Engine.",
        )

    def _growth_models(self):
        from apps.growth_engine.models import Lead, LeadInteraction, LeadSource

        return Lead, LeadSource, LeadInteraction

    def _growth_services(self):
        from apps.growth_engine.services.lead_service import LeadService

        return LeadService

    def _notify_team_if_needed(self, *, livia_lead, crm_lead):
        if not is_lead_ready_for_notification(livia_lead):
            return
        if not (livia_lead.phone or livia_lead.email):
            return
        if (crm_lead.metadata or {}).get("source") != "livia_assistant":
            return
        if self._conversation_already_notified(livia_lead):
            return

        recipients = list(
            getattr(settings, "LIVIA_LEAD_NOTIFICATION_RECIPIENTS", ["contato@smartcontrolbrasil.com.br"]) or []
        )
        bcc_recipients = list(
            getattr(settings, "LIVIA_LEAD_NOTIFICATION_BCC", ["engenharia@smartcontrolbrasil.com.br"]) or []
        )
        if not recipients:
            return

        display_name = (livia_lead.name or livia_lead.company or "Lead sem identificação").strip()
        subject = f"Novo lead da Lívia - {display_name}"
        timestamp = timezone.localtime(timezone.now()).strftime("%d/%m/%Y %H:%M")
        body = build_lead_notification_body(livia_lead, timestamp=timestamp)

        email = EmailMultiAlternatives(
            subject=subject,
            body=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "engenharia@smartcontrolbrasil.com.br"),
            to=recipients,
            bcc=bcc_recipients,
        )
        email.send(fail_silently=False)

        updated_reference = dict(livia_lead.crm_reference or {})
        updated_reference["notification_sent_at"] = timezone.now().isoformat()
        updated_reference["notification_subject"] = subject
        updated_reference["notification_recipients"] = recipients
        livia_lead.crm_reference = updated_reference
        livia_lead.save(update_fields=["crm_reference"])

    def _conversation_already_notified(self, livia_lead):
        for capture in livia_lead.conversation.lead_captures.all():
            if capture.crm_reference.get("notification_sent_at"):
                return True
        return False

    def _notify_n8n_if_needed(self, *, livia_lead, crm_lead):
        webhook_url = str(getattr(settings, "N8N_LIVIA_LEAD_WEBHOOK_URL", "") or "").strip()
        if not webhook_url:
            return
        if self._conversation_already_webhooked(livia_lead):
            return
        if not is_lead_ready_for_notification(livia_lead):
            return
        if not (livia_lead.phone or livia_lead.email):
            return
        if (crm_lead.metadata or {}).get("source") != "livia_assistant":
            return

        payload = {
            "event": "livia.lead.qualified",
            "source": "livia_assistant",
            "lead": {
                "id": str(crm_lead.id),
                "contact_name": crm_lead.contact_name or "",
                "company_name": crm_lead.company_name or "",
                "city": crm_lead.city or "",
                "phone": crm_lead.phone or "",
                "whatsapp": crm_lead.whatsapp or "",
                "email": crm_lead.email or "",
                "notes": crm_lead.notes or "",
                "status": crm_lead.status or "",
                "source": getattr(crm_lead.source, "name", "") if crm_lead.source_id else "",
            },
            "capture": {
                "id": str(livia_lead.id),
                "service_interest": livia_lead.service_interest or "",
                "conversation_id": str(livia_lead.conversation_id),
                "created_at": livia_lead.created_at.isoformat() if livia_lead.created_at else "",
                "updated_at": livia_lead.created_at.isoformat() if livia_lead.created_at else "",
            },
        }

        headers = {"Content-Type": "application/json"}
        token = str(getattr(settings, "N8N_LIVIA_LEAD_WEBHOOK_TOKEN", "") or "").strip()
        if token:
            headers["X-Smart360-Token"] = token
        timeout = int(getattr(settings, "N8N_LIVIA_LEAD_WEBHOOK_TIMEOUT", 5) or 5)
        request = Request(
            webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urlopen(request, timeout=timeout) as response:
                status_code = getattr(response, "status", None) or response.getcode()
            if 200 <= int(status_code) < 300:
                self._mark_n8n_webhook_sent(livia_lead)
                logger.info("Webhook n8n da Lívia enviado com sucesso. capture_id=%s status=%s", livia_lead.id, status_code)
                return
            logger.warning("Webhook n8n da Lívia retornou status não esperado. capture_id=%s status=%s", livia_lead.id, status_code)
        except HTTPError as exc:
            logger.warning("Webhook n8n da Lívia falhou com HTTPError. capture_id=%s status=%s", livia_lead.id, exc.code)
        except URLError as exc:
            logger.warning("Webhook n8n da Lívia falhou com URLError. capture_id=%s reason=%s", livia_lead.id, exc.reason)
        except Exception as exc:  # pragma: no cover - defensive integration guard
            logger.warning("Webhook n8n da Lívia falhou com exceção. capture_id=%s type=%s", livia_lead.id, exc.__class__.__name__)

    def _mark_n8n_webhook_sent(self, livia_lead):
        updated_reference = dict(livia_lead.crm_reference or {})
        updated_reference["n8n_livia_lead_webhook_sent_at"] = timezone.now().isoformat()
        livia_lead.crm_reference = updated_reference
        livia_lead.save(update_fields=["crm_reference"])

    def _conversation_already_webhooked(self, livia_lead):
        for capture in livia_lead.conversation.lead_captures.all():
            if capture.crm_reference.get("n8n_livia_lead_webhook_sent_at"):
                return True
        return False
