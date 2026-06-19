from __future__ import annotations

from apps.ai_agents_center.agents.base import (
    AgentActionProposalPayload,
    AgentRecommendationPayload,
    BaseSpecializedAgent,
)
from apps.ai_agents_center.models import CommercialOpportunity
from apps.ai_agents_center.services.commercial_intelligence import CommercialIntelligenceService, UNCONFIRMED
from apps.ai_agents_center.services.opportunity_builder import OpportunityBuilderService


class EduardoCommercialIntelligenceAgent(BaseSpecializedAgent):
    slug = "eduardo-commercial-intelligence-agent"
    trigger_domains = ("growth", "lead", "commercial", "market_intelligence", "public_opportunity")

    def build_context(self, *, company=None, site=None, trigger_reference="", triggered_by=None):
        return CommercialIntelligenceService.build_context(
            company=company,
            site=site,
            trigger_reference=trigger_reference,
            triggered_by=triggered_by,
            definition=self.definition,
        )

    def generate(self, *, context: dict):
        analysis = CommercialIntelligenceService.analyze(context=context)
        opportunity_data = analysis.opportunity
        company_name = opportunity_data.get("company_name") or "oportunidade comercial"
        products = analysis.recommended_products or [UNCONFIRMED]
        services = analysis.recommended_services or [UNCONFIRMED]
        problems_text = "; ".join(opportunity_data.get("problems") or [UNCONFIRMED])
        commercial_opportunity = OpportunityBuilderService.build_from_analysis(
            analysis=analysis,
            company_id=(context.get("company") or {}).get("id"),
            agent_run_id=context.get("agent_run_id"),
            source=opportunity_data.get("source") or CommercialOpportunity.Source.MANUAL,
        )
        context["commercial_opportunity_public_id"] = str(commercial_opportunity.public_id)

        recommendation = AgentRecommendationPayload(
            recommendation_type="marketplace",
            title=f"EDU: revisar oportunidade {company_name}",
            summary=(
                f"Oportunidade comercial criada com score {commercial_opportunity.commercial_score} "
                f"e confianca {commercial_opportunity.confidence_score}. "
                f"Problemas: {problems_text}."
            ),
            explanation=(
                "A analise separa fatos de hipoteses e criou uma CommercialOpportunity auditavel. "
                "O EDU nao converte oportunidades em leads automaticamente."
            ),
            evidence_summary="; ".join(analysis.facts or [UNCONFIRMED]),
            suggested_action=(
                "Revisar a oportunidade para aprovacao humana e posterior conversao manual em lead."
                if commercial_opportunity.status == CommercialOpportunity.Status.READY_FOR_REVIEW
                else "Enriquecer dados publicos antes da revisao comercial."
            ),
            severity=analysis.severity,
            priority=analysis.priority,
            attention_score=analysis.score_value,
            requires_human_approval=True,
            entity_type="commercial_opportunity",
            entity_id=str(commercial_opportunity.public_id),
            payload={
                "commercial_opportunity_public_id": str(commercial_opportunity.public_id),
                "profile": {
                    "name": opportunity_data.get("company_name") or UNCONFIRMED,
                    "segment": opportunity_data.get("segment") or UNCONFIRMED,
                    "city": opportunity_data.get("city") or UNCONFIRMED,
                    "state": opportunity_data.get("state") or UNCONFIRMED,
                    "estimated_size": opportunity_data.get("estimated_size") or UNCONFIRMED,
                },
                "opportunities": {
                    "problems": opportunity_data.get("problems") or [],
                    "recommended_products": products,
                    "recommended_services": services,
                },
                "score": {"label": analysis.score_label, "value": analysis.score_value},
                "confidence": str(commercial_opportunity.confidence_score),
                "status": commercial_opportunity.status,
                "facts": analysis.facts,
                "hypotheses": analysis.hypotheses,
                "missing_information": analysis.missing_information,
            },
        )

        if commercial_opportunity.status == CommercialOpportunity.Status.READY_FOR_REVIEW:
            proposal = AgentActionProposalPayload(
                action_type="review_commercial_opportunity",
                target_entity="commercial_opportunity",
                target_entity_id=str(commercial_opportunity.public_id),
                title=f"Revisar oportunidade EDU: {company_name}",
                summary="Oportunidade pronta para revisao humana antes de virar lead.",
                proposed_payload={
                    "commercial_opportunity_public_id": str(commercial_opportunity.public_id),
                    "status": commercial_opportunity.status,
                    "confidence": str(commercial_opportunity.confidence_score),
                    "next_step": "approve_or_reject",
                },
                priority=analysis.priority,
                approval_required=True,
            )
        else:
            proposal = AgentActionProposalPayload(
                action_type="enrich_commercial_opportunity",
                target_entity="commercial_opportunity",
                target_entity_id=str(commercial_opportunity.public_id),
                title="Enriquecer oportunidade EDU",
                summary="A oportunidade ainda nao tem confianca suficiente para revisao comercial.",
                proposed_payload={
                    "commercial_opportunity_public_id": str(commercial_opportunity.public_id),
                    "missing_information": analysis.missing_information,
                    "required_confidence": str(OpportunityBuilderService.READY_CONFIDENCE_THRESHOLD),
                    "current_confidence": str(commercial_opportunity.confidence_score),
                },
                priority="medium",
                approval_required=True,
            )

        output_summary = (
            f"EDU criou CommercialOpportunity {commercial_opportunity.public_id} para {company_name}: "
            f"score {commercial_opportunity.commercial_score}, confianca {commercial_opportunity.confidence_score}, "
            f"status {commercial_opportunity.status}."
        )
        return [recommendation], [proposal], output_summary
