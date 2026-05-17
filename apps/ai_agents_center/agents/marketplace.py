from __future__ import annotations

from apps.ai_agents_center.agents.base import (
    AgentActionProposalPayload,
    AgentRecommendationPayload,
    BaseSpecializedAgent,
)


def get_marketplace_allocation_intelligence_service():
    from apps.ai_agents_center.services.marketplace_allocation_intelligence import MarketplaceAllocationIntelligenceService

    return MarketplaceAllocationIntelligenceService


class MarketplaceAllocationAgent(BaseSpecializedAgent):
    slug = "marketplace-agent"
    trigger_domains = ("service_request", "offer", "assignment", "matching", "sla", "marketplace")

    def build_context(self, *, company=None, site=None, trigger_reference="", triggered_by=None):
        intelligence_service = get_marketplace_allocation_intelligence_service()
        scope = intelligence_service.resolve_scope_from_trigger(
            company=company,
            site=site,
            trigger_reference=trigger_reference,
        )
        return intelligence_service.build_scope_context(
            company=company,
            site=scope["site"],
            service_request=scope["service_request"],
            category=scope["category"],
            target_date=scope["target_date"],
            trigger_reference=trigger_reference,
            triggered_by=triggered_by,
            definition=self.definition,
        )

    def generate(self, *, context: dict):
        intelligence_service = get_marketplace_allocation_intelligence_service()
        recommendation_drafts, proposal_drafts, health_flags, output_summary = intelligence_service.analyze_scope(
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
        context["marketplace_health_flags"] = health_flags
        return recommendations, proposals, output_summary
