from __future__ import annotations

from apps.ai_agents_center.agents.base import (
    AgentActionProposalPayload,
    AgentRecommendationPayload,
    BaseSpecializedAgent,
)
from apps.ai_agents_center.services.maintenance_intelligence import MaintenanceIntelligenceService
from apps.smart_system.models import Asset, AssetCategory


class MaintenanceIntelligenceAgent(BaseSpecializedAgent):
    slug = "maintenance-agent"
    trigger_domains = ("asset", "failure", "preventive", "work_order", "checklist", "analytics")

    def build_context(self, *, company=None, site=None, trigger_reference="", triggered_by=None):
        asset = None
        category = None
        if trigger_reference.startswith("asset:"):
            asset = Asset.objects.filter(public_id=trigger_reference.split(":", 1)[1]).select_related("operational_site", "category").first()
        if trigger_reference.startswith("category:"):
            category = AssetCategory.objects.filter(slug=trigger_reference.split(":", 1)[1]).first()
        return MaintenanceIntelligenceService.build_scope_context(
            company=company,
            site=site,
            asset=asset,
            category=category,
            trigger_reference=trigger_reference,
            triggered_by=triggered_by,
            definition=self.definition,
        )

    def generate(self, *, context: dict):
        recommendation_drafts, proposal_drafts, attention_flags, output_summary = MaintenanceIntelligenceService.analyze_scope(
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
        context["attention_flags"] = attention_flags
        return recommendations, proposals, output_summary
