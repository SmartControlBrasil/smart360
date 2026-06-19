from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.ai_agents_center.models import CommercialOpportunity
from apps.ai_agents_center.services.commercial_intelligence import UNCONFIRMED
from apps.growth_engine.services.lead_service import LeadService


class OpportunityBuilderService:
    READY_CONFIDENCE_THRESHOLD = Decimal("0.70")
    DUPLICATE_OPEN_STATUSES = {
        CommercialOpportunity.Status.NEW,
        CommercialOpportunity.Status.ENRICHING,
        CommercialOpportunity.Status.READY_FOR_REVIEW,
        CommercialOpportunity.Status.APPROVED,
    }
    VALID_SOURCES = {choice[0] for choice in CommercialOpportunity.Source.choices}

    @classmethod
    def build_from_analysis(cls, *, analysis, company=None, company_id=None, agent_run=None, agent_run_id=None, source="manual"):
        opportunity = analysis.opportunity
        confidence_score = cls.calculate_confidence(analysis=analysis)
        status = (
            CommercialOpportunity.Status.READY_FOR_REVIEW
            if confidence_score >= cls.READY_CONFIDENCE_THRESHOLD
            else CommercialOpportunity.Status.ENRICHING
        )
        products = analysis.recommended_products or []
        services = analysis.recommended_services or []
        problem_detected = "; ".join(opportunity.get("problems") or [UNCONFIRMED])
        recommended_solution = "; ".join(services or products or [UNCONFIRMED])
        recommended_product = "; ".join(products)
        opportunity_description = cls._description(
            opportunity=opportunity,
            analysis=analysis,
            problem_detected=problem_detected,
            recommended_solution=recommended_solution,
            recommended_product=recommended_product,
        )
        source = source if source in cls.VALID_SOURCES else CommercialOpportunity.Source.MANUAL
        relation_fields = cls._relation_fields(company=company, company_id=company_id, agent_run=agent_run, agent_run_id=agent_run_id)
        metadata = {
            "origin_agent": "eduardo-commercial-intelligence-agent",
            "facts": analysis.facts,
            "hypotheses": analysis.hypotheses,
            "missing_information": analysis.missing_information,
            "score_label": analysis.score_label,
            "institutional_contacts": opportunity.get("institutional_contacts") or [],
            "website": opportunity.get("website") or "",
            "evidence": opportunity.get("evidence") or [],
            "source_urls": opportunity.get("source_urls") or [],
            "recommended_services": services,
            "recommended_products": products,
            "compliance": "Oportunidade criada sem conversao automatica para lead.",
        }
        defaults = {
            **relation_fields,
            "segment": opportunity.get("segment") or "",
            "city": opportunity.get("city") or "",
            "state": opportunity.get("state") or "",
            "title": f"Oportunidade EDU: {opportunity.get('company_name') or 'empresa nao confirmada'}",
            "opportunity_description": opportunity_description,
            "recommended_solution": recommended_solution,
            "recommended_product": recommended_product,
            "commercial_score": analysis.score_value,
            "confidence_score": confidence_score,
            "status": status,
            "metadata": metadata,
        }
        company_name = opportunity.get("company_name") or UNCONFIRMED
        duplicate = cls.find_duplicate(company_name=company_name, source=source, problem_detected=problem_detected)
        if duplicate is not None:
            return cls._update_duplicate(duplicate, defaults)
        return CommercialOpportunity.objects.create(
            company_name=company_name,
            source=source,
            problem_detected=problem_detected,
            **defaults,
        )

    @classmethod
    def find_duplicate(cls, *, company_name, source, problem_detected):
        if not company_name or company_name == UNCONFIRMED:
            return None
        return (
            CommercialOpportunity.objects.filter(
                company_name__iexact=company_name.strip(),
                source=source,
                problem_detected__iexact=problem_detected.strip(),
                status__in=cls.DUPLICATE_OPEN_STATUSES,
            )
            .order_by("-updated_at", "-id")
            .first()
        )

    @classmethod
    def calculate_confidence(cls, *, analysis):
        opportunity = analysis.opportunity
        confidence = Decimal("0.10")
        if opportunity.get("company_name"):
            confidence += Decimal("0.18")
        if opportunity.get("segment"):
            confidence += Decimal("0.10")
        if opportunity.get("city") and opportunity.get("state"):
            confidence += Decimal("0.10")
        if opportunity.get("website"):
            confidence += Decimal("0.10")
        if opportunity.get("problems"):
            confidence += Decimal("0.18")
        if opportunity.get("evidence"):
            confidence += min(Decimal(len(opportunity.get("evidence", []))) * Decimal("0.08"), Decimal("0.16"))
        if opportunity.get("institutional_contacts"):
            confidence += Decimal("0.08")
        if analysis.recommended_products or analysis.recommended_services:
            confidence += Decimal("0.10")
        missing_penalty = min(Decimal(len(analysis.missing_information)) * Decimal("0.04"), Decimal("0.20"))
        confidence = max(Decimal("0.00"), min(confidence - missing_penalty, Decimal("1.00")))
        return confidence.quantize(Decimal("0.01"))

    @classmethod
    def mark_ready_for_review(cls, *, opportunity, user=None):
        if opportunity.confidence_score < cls.READY_CONFIDENCE_THRESHOLD:
            raise ValueError("Only opportunities with confidence >= 0.70 can be marked as READY_FOR_REVIEW.")
        opportunity.status = CommercialOpportunity.Status.READY_FOR_REVIEW
        opportunity.reviewed_by = user
        opportunity.reviewed_at = timezone.now()
        opportunity.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        return opportunity

    @classmethod
    def approve(cls, *, opportunity, user=None):
        if opportunity.status not in {CommercialOpportunity.Status.NEW, CommercialOpportunity.Status.READY_FOR_REVIEW}:
            raise ValueError("Only NEW or READY_FOR_REVIEW opportunities can be approved.")
        opportunity.status = CommercialOpportunity.Status.APPROVED
        opportunity.reviewed_by = user
        opportunity.reviewed_at = timezone.now()
        opportunity.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        return opportunity

    @classmethod
    def reject(cls, *, opportunity, user=None, reason=""):
        if opportunity.status not in {CommercialOpportunity.Status.NEW, CommercialOpportunity.Status.READY_FOR_REVIEW}:
            raise ValueError("Only NEW or READY_FOR_REVIEW opportunities can be rejected.")
        opportunity.status = CommercialOpportunity.Status.REJECTED
        opportunity.reviewed_by = user
        opportunity.reviewed_at = timezone.now()
        opportunity.metadata = {**opportunity.metadata, "rejection_reason": reason}
        opportunity.save(update_fields=["status", "reviewed_by", "reviewed_at", "metadata", "updated_at"])
        return opportunity

    @classmethod
    @transaction.atomic
    def convert_to_lead(cls, *, opportunity, user=None):
        if opportunity.status == CommercialOpportunity.Status.CONVERTED_TO_LEAD or opportunity.lead_id:
            raise ValueError("Commercial opportunity has already been converted to a lead.")
        if opportunity.status != CommercialOpportunity.Status.APPROVED:
            raise ValueError("Only APPROVED opportunities can be converted to Growth Engine leads.")
        metadata = opportunity.metadata or {}
        lead = LeadService.create_lead(
            user=user,
            validated_data={
                "company_name": opportunity.company_name,
                "contact_name": "",
                "email": cls._first_contact(metadata.get("institutional_contacts") or [], "@"),
                "phone": "",
                "whatsapp": "",
                "website": metadata.get("website") or "",
                "city": opportunity.city,
                "state": opportunity.state,
                "status": "new",
                "notes": cls._lead_notes(opportunity=opportunity),
                "metadata": {
                    "origin_opportunity_public_id": str(opportunity.public_id),
                    "origin_agent": metadata.get("origin_agent", "eduardo-commercial-intelligence-agent"),
                    "source": opportunity.source,
                    "problem_detected": opportunity.problem_detected,
                    "opportunity_description": opportunity.opportunity_description,
                    "recommended_solution": opportunity.recommended_solution,
                    "recommended_product": opportunity.recommended_product,
                    "opportunity_commercial_score": opportunity.commercial_score,
                    "opportunity_confidence_score": str(opportunity.confidence_score),
                },
            },
        )
        opportunity.lead = lead
        opportunity.status = CommercialOpportunity.Status.CONVERTED_TO_LEAD
        opportunity.converted_by = user
        opportunity.converted_at = timezone.now()
        opportunity.save(update_fields=["lead", "status", "converted_by", "converted_at", "updated_at"])
        return lead

    @staticmethod
    def _relation_fields(*, company=None, company_id=None, agent_run=None, agent_run_id=None):
        fields = {}
        if company is not None:
            fields["company"] = company
        elif company_id is not None:
            fields["company_id"] = company_id
        if agent_run is not None:
            fields["agent_run"] = agent_run
        elif agent_run_id is not None:
            fields["agent_run_id"] = agent_run_id
        return fields

    @staticmethod
    def _description(*, opportunity, analysis, problem_detected, recommended_solution, recommended_product):
        parts = [
            f"Problema detectado: {problem_detected}",
            f"Solucao sugerida: {recommended_solution}",
        ]
        if recommended_product:
            parts.append(f"Produto recomendado: {recommended_product}")
        parts.append(f"Score EDU: {analysis.score_label} ({analysis.score_value}/100)")
        if opportunity.get("evidence"):
            parts.append(f"Evidencias: {'; '.join(opportunity.get('evidence') or [])}")
        return "\n".join(parts)

    @staticmethod
    def _update_duplicate(opportunity, defaults):
        immutable_statuses = {
            CommercialOpportunity.Status.APPROVED,
            CommercialOpportunity.Status.CONVERTED_TO_LEAD,
        }
        for field, value in defaults.items():
            if field == "status" and opportunity.status in immutable_statuses:
                continue
            setattr(opportunity, field, value)
        opportunity.metadata = {**(opportunity.metadata or {}), **defaults.get("metadata", {}), "deduplicated": True}
        opportunity.save()
        return opportunity

    @staticmethod
    def _first_contact(contacts, marker):
        for contact in contacts:
            if marker in contact:
                return contact
        return ""

    @staticmethod
    def _lead_notes(*, opportunity):
        return "\n".join(
            [
                f"Origem: CommercialOpportunity {opportunity.public_id}",
                f"Problema detectado: {opportunity.problem_detected}",
                f"Descricao da oportunidade: {opportunity.opportunity_description}",
                f"Solucao recomendada: {opportunity.recommended_solution}",
                f"Produto recomendado: {opportunity.recommended_product or UNCONFIRMED}",
                f"Score EDU: {opportunity.commercial_score}",
                f"Confianca EDU: {opportunity.confidence_score}",
            ]
        )
