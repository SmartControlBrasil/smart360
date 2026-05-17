from __future__ import annotations

from apps.ai_agents_center.agents.base import (
    AgentActionProposalPayload,
    AgentRecommendationPayload,
    BaseSpecializedAgent,
)
from apps.ai_agents_center.services.profitability_intelligence import ProfitabilityIntelligenceService


class ProfitabilityAgent(BaseSpecializedAgent):
    slug = "profitability-agent"
    trigger_domains = ("billing", "contracts", "work_order", "quote", "stock", "analytics", "routing")

    def build_context(self, *, company=None, site=None, trigger_reference="", triggered_by=None):
        scope = ProfitabilityIntelligenceService.resolve_scope_from_trigger(
            company=company,
            site=site,
            trigger_reference=trigger_reference,
        )
        return ProfitabilityIntelligenceService.build_scope_context(
            company=company,
            site=scope["site"],
            client=scope["client"],
            contract=scope["contract"],
            technician=scope["technician"],
            target_date=scope["target_date"],
            trigger_reference=trigger_reference,
            triggered_by=triggered_by,
            definition=self.definition,
        )

    def generate(self, *, context: dict):
        recommendation_drafts, proposal_drafts, profitability_flags, output_summary = ProfitabilityIntelligenceService.analyze_scope(
            context=context,
            definition=self.definition,
        )
        recommendations = [
            AgentRecommendationPayload(
                recommendation_type=item.recommendation_type,
                title=item.title,
                summary=item.summary,
                explanation=item.explanation,
                evidence_summary=item.evidence_summary,
                suggested_action=item.suggested_action,
                severity=item.severity,
                priority=item.priority,
                attention_score=item.attention_score,
                requires_human_approval=item.requires_human_approval,
                entity_type=item.entity_type,
                entity_id=item.entity_id,
                payload=item.payload,
            )
            for item in recommendation_drafts
        ]
        proposals = [
            AgentActionProposalPayload(
                action_type=item.action_type,
                target_entity=item.target_entity,
                target_entity_id=item.target_entity_id,
                title=item.title,
                summary=item.summary,
                proposed_payload=item.proposed_payload,
                priority=item.priority,
                approval_required=item.approval_required,
            )
            for item in proposal_drafts
        ]
        context["profitability_flags"] = profitability_flags
        return recommendations, proposals, output_summary
