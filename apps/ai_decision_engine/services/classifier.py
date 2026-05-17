from __future__ import annotations

from dataclasses import dataclass

from apps.ai_agents_center.models import AgentActionProposal

from .catalog import ACTION_CATALOG, ALIAS_LOOKUP


@dataclass(frozen=True)
class ActionClassification:
    action_type: str
    normalized_action_type: str
    risk_level: str
    autonomy_level: int
    tenant_scope_mode: str
    rollback_required: bool
    requires_human_approval: bool
    can_auto_execute: bool
    approver_role_slugs: list[str]
    signals: list[str]
    description: str


class ActionProposalClassifier:
    @classmethod
    def classify(cls, proposal: AgentActionProposal) -> ActionClassification:
        normalized = ALIAS_LOOKUP.get(proposal.action_type, proposal.action_type)
        entry = ACTION_CATALOG.get(normalized)
        if entry is None:
            return ActionClassification(
                action_type=proposal.action_type,
                normalized_action_type=proposal.action_type,
                risk_level="critical",
                autonomy_level=0,
                tenant_scope_mode="company",
                rollback_required=False,
                requires_human_approval=True,
                can_auto_execute=False,
                approver_role_slugs=["company-admin", "super-admin"],
                signals=["unknown_action_type"],
                description="Action type sem catalogo explicito do Decision Engine.",
            )

        payload = proposal.proposed_payload or {}
        risk_level = entry.risk_level
        signals = ["catalog_match"]
        if proposal.priority in {"immediate", "urgent"} and risk_level in {"low", "medium"}:
            risk_level = "high"
            signals.append("priority_escalation")
        if proposal.target_entity in {"maintenance_contract", "billing_contract"} and proposal.action_type in {
            "suggest_contract_repricing",
            "review_contract_profitability_shift",
        }:
            risk_level = "critical"
            signals.append("contract_criticality")
        if payload.get("marketplace_candidates") and normalized == "assign_marketplace_candidate_proposal":
            signals.append("marketplace_candidate_context")
        if payload.get("conflicts") and normalized == "create_schedule_adjustment_proposal":
            signals.append("scheduling_conflicts")

        can_auto_execute = entry.supports_execution and not entry.requires_human_approval and risk_level == "low"
        if normalized == "flag_contract_profitability_attention" and risk_level == "medium":
            can_auto_execute = True
            signals.append("safe_flag_materialization")
        if normalized == "create_investigation_task":
            can_auto_execute = True
            signals.append("safe_investigation_materialization")

        return ActionClassification(
            action_type=proposal.action_type,
            normalized_action_type=normalized,
            risk_level=risk_level,
            autonomy_level=entry.autonomy_level,
            tenant_scope_mode=entry.tenant_scope_mode,
            rollback_required=entry.rollback_required,
            requires_human_approval=entry.requires_human_approval or risk_level in {"high", "critical"},
            can_auto_execute=can_auto_execute and risk_level in {"low", "medium"},
            approver_role_slugs=list(entry.approver_role_slugs),
            signals=signals,
            description=entry.description,
        )

