from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentRecommendationPayload:
    recommendation_type: str
    title: str
    summary: str
    explanation: str = ""
    evidence_summary: str = ""
    suggested_action: str = ""
    severity: str = "medium"
    priority: str = "medium"
    attention_score: int = 0
    requires_human_approval: bool = True
    payload: dict = field(default_factory=dict)
    entity_type: str = ""
    entity_id: str = ""


@dataclass
class AgentActionProposalPayload:
    action_type: str
    target_entity: str
    target_entity_id: str
    title: str = ""
    summary: str = ""
    proposed_payload: dict = field(default_factory=dict)
    priority: str = "medium"
    approval_required: bool = True


class BaseSpecializedAgent:
    slug = ""
    trigger_domains: tuple[str, ...] = ()

    def __init__(self, *, definition):
        self.definition = definition

    def build_context(self, *, company=None, site=None, trigger_reference="", triggered_by=None):
        raise NotImplementedError

    def generate(self, *, context: dict):
        raise NotImplementedError
