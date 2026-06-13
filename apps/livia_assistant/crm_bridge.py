import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.utils import timezone

from .models import LiviaHandoffRequest, LiviaLeadCapture

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
        if not self.can_integrate() or not livia_lead.is_qualified:
            return None

        Lead, LeadSource, LeadInteraction = self._growth_models()
        LeadService = self._growth_services()
        source = self._get_or_create_source(LeadSource)
        crm_lead = self._find_existing_lead(Lead, livia_lead, source)
        payload = self._payload_for_livia_lead(livia_lead, source)

        if crm_lead is None:
            crm_lead = LeadService.create_lead(user=None, validated_data=payload)
        else:
            merged_metadata = {**(crm_lead.metadata or {}), **payload.pop("metadata", {})}
            payload["metadata"] = merged_metadata
            crm_lead = LeadService.update_lead(lead=crm_lead, validated_data=payload, user=None)

        livia_lead.crm_lead_id = crm_lead.id
        livia_lead.crm_reference = {
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
        return crm_lead

    def create_followup_task(self, livia_lead) -> object | None:
        if not self.can_integrate():
            return None
        Lead, LeadSource, LeadInteraction = self._growth_models()
        source = self._get_or_create_source(LeadSource)
        crm_lead = self._find_existing_lead(Lead, livia_lead, source)
        if crm_lead is None and livia_lead.is_qualified:
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
        if livia_lead.crm_lead_id:
            lead = Lead.objects.filter(pk=livia_lead.crm_lead_id).first()
            if lead:
                return lead
        if livia_lead.email:
            lead = Lead.objects.filter(email__iexact=livia_lead.email, source=source).first()
            if lead:
                return lead
        if livia_lead.phone:
            return (
                Lead.objects.filter(phone=livia_lead.phone, source=source).first()
                or Lead.objects.filter(whatsapp=livia_lead.phone, source=source).first()
            )
        return None

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
        if not livia_lead.is_qualified:
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
        body = "\n".join(
            [
                "Novo lead qualificado pela Lívia",
                "",
                f"Nome: {livia_lead.name or 'Não informado'}",
                f"Empresa: {livia_lead.company or 'Não informado'}",
                f"Cidade: {livia_lead.city or 'Não informada'}",
                f"Telefone/WhatsApp: {livia_lead.phone or 'Não informado'}",
                f"E-mail: {livia_lead.email or 'Não informado'}",
                f"Interesse/problema: {livia_lead.notes or 'Não informado'}",
                "Origem: livia_assistant",
                f"Data/hora: {timestamp}",
            ]
        )

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
