from __future__ import annotations

from apps.ai_agents_center.agents.base import (
    AgentActionProposalPayload,
    AgentRecommendationPayload,
    BaseSpecializedAgent,
)
from apps.ai_agents_center.services.commercial_intelligence import CommercialIntelligenceService, UNCONFIRMED


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
        opportunity = analysis.opportunity
        company_name = opportunity.get("company_name") or "oportunidade comercial"
        products = analysis.recommended_products or [UNCONFIRMED]
        services = analysis.recommended_services or [UNCONFIRMED]

        recommendation = AgentRecommendationPayload(
            recommendation_type="marketplace",
            title=f"EDU: analisar {company_name}",
            summary=(
                f"Potencial comercial classificado como {analysis.score_label}. "
                f"Problemas: {'; '.join(opportunity.get('problems') or [UNCONFIRMED])}."
            ),
            explanation=(
                "A analise separa fatos de hipoteses e recomenda somente proximos passos baseados "
                "em evidencias publicas ou informacoes fornecidas legitimamente."
            ),
            evidence_summary="; ".join(analysis.facts or [UNCONFIRMED]),
            suggested_action=(
                "Criar lead no Growth Engine para qualificacao comercial."
                if analysis.identified
                else "Coletar evidencia publica minima antes de criar lead comercial."
            ),
            severity=analysis.severity,
            priority=analysis.priority,
            attention_score=analysis.score_value,
            requires_human_approval=True,
            entity_type="commercial_opportunity",
            entity_id=opportunity.get("company_name") or "unconfirmed-opportunity",
            payload={
                "profile": {
                    "name": opportunity.get("company_name") or UNCONFIRMED,
                    "segment": opportunity.get("segment") or UNCONFIRMED,
                    "city": opportunity.get("city") or UNCONFIRMED,
                    "state": opportunity.get("state") or UNCONFIRMED,
                    "estimated_size": opportunity.get("estimated_size") or UNCONFIRMED,
                },
                "indicators": {
                    "digital_presence": opportunity.get("digital_presence") or UNCONFIRMED,
                    "technology_level": opportunity.get("technology_level") or UNCONFIRMED,
                    "institutional_contacts": opportunity.get("institutional_contacts") or [],
                    "financial_capacity": opportunity.get("financial_capacity") or UNCONFIRMED,
                    "innovation_potential": opportunity.get("innovation_potential") or UNCONFIRMED,
                },
                "opportunities": {
                    "problems": opportunity.get("problems") or [],
                    "recommended_products": products,
                    "recommended_services": services,
                },
                "score": {"label": analysis.score_label, "value": analysis.score_value},
                "facts": analysis.facts,
                "hypotheses": analysis.hypotheses,
                "missing_information": analysis.missing_information,
            },
        )

        proposals = []
        if analysis.identified:
            proposals.append(
                AgentActionProposalPayload(
                    action_type="create_growth_lead_from_public_opportunity",
                    target_entity="growth_lead",
                    target_entity_id=opportunity.get("company_name", ""),
                    title=f"Criar lead EDU: {company_name}",
                    summary=f"Registrar oportunidade {analysis.score_label} no Growth Engine.",
                    proposed_payload=CommercialIntelligenceService.build_lead_payload(analysis),
                    priority=analysis.priority,
                    approval_required=True,
                )
            )
        else:
            proposals.append(
                AgentActionProposalPayload(
                    action_type="enrich_growth_lead_public_evidence",
                    target_entity="commercial_opportunity",
                    target_entity_id=company_name,
                    title="Coletar evidencias antes de gerar lead",
                    summary="A oportunidade ainda nao tem dados suficientes para cadastro comercial confiavel.",
                    proposed_payload={
                        "missing_information": analysis.missing_information,
                        "required_minimum": ["empresa", "problema identificado", "fonte publica ou informacao legitima"],
                    },
                    priority="medium",
                    approval_required=True,
                )
            )

        output_summary = (
            f"EDU avaliou {company_name}: {analysis.score_label} ({analysis.score_value}/100). "
            f"Produtos: {', '.join(products)}. Servicos: {', '.join(services)}."
        )
        return [recommendation], proposals, output_summary

