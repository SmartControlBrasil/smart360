from __future__ import annotations

from dataclasses import dataclass

from django.db import models

from apps.access_control_center.models import UserRoleAssignment
from apps.ai_decision_engine.models import AgentDecision, DecisionPolicy


@dataclass(frozen=True)
class PolicyEvaluationResult:
    policy: DecisionPolicy | None
    outcome: str
    reason: str
    requires_human_approval: bool
    can_auto_execute: bool
    escalation_target: str
    approver_role_slugs: list[str]
    explainability_payload: dict


class DecisionPolicyEngine:
    @staticmethod
    def resolve_policy(*, normalized_action_type: str) -> DecisionPolicy | None:
        return (
            DecisionPolicy.objects.filter(action_type=normalized_action_type, enabled=True)
            .order_by("-updated_at")
            .first()
        )

    @classmethod
    def evaluate(cls, *, proposal, classification, company=None, site=None) -> PolicyEvaluationResult:
        policy = cls.resolve_policy(normalized_action_type=classification.normalized_action_type)
        explainability = {
            "classification": {
                "action_type": classification.action_type,
                "normalized_action_type": classification.normalized_action_type,
                "risk_level": classification.risk_level,
                "autonomy_level": classification.autonomy_level,
                "tenant_scope_mode": classification.tenant_scope_mode,
                "signals": classification.signals,
                "description": classification.description,
            },
            "tenant": {
                "company_id": getattr(company, "id", None),
                "company_status": getattr(company, "status", ""),
                "site_id": getattr(site, "id", None),
            },
        }
        if policy is None:
            return PolicyEvaluationResult(
                policy=None,
                outcome=AgentDecision.DecisionStatus.AUTO_BLOCKED,
                reason="Nenhuma policy habilitada para este action_type.",
                requires_human_approval=False,
                can_auto_execute=False,
                escalation_target="",
                approver_role_slugs=[],
                explainability_payload=explainability,
            )
        explainability["policy"] = {
            "slug": policy.slug,
            "risk_level": policy.risk_level,
            "autonomy_level": policy.autonomy_level,
            "requires_human_approval": policy.requires_human_approval,
            "tenant_scope_mode": policy.tenant_scope_mode,
            "approver_role_slugs": policy.approver_role_slugs,
            "config": policy.config,
        }
        if company is not None and getattr(company, "status", "") not in {"active", ""}:
            return PolicyEvaluationResult(
                policy=policy,
                outcome=AgentDecision.DecisionStatus.AUTO_BLOCKED,
                reason=f"Empresa fora de estado elegivel para execucao: {company.status}.",
                requires_human_approval=False,
                can_auto_execute=False,
                escalation_target="",
                approver_role_slugs=list(policy.approver_role_slugs),
                explainability_payload=explainability,
            )
        if policy.tenant_scope_mode == DecisionPolicy.TenantScopeMode.SITE and site is None:
            return PolicyEvaluationResult(
                policy=policy,
                outcome=AgentDecision.DecisionStatus.ESCALATED,
                reason="Policy exige escopo de unidade/site, mas a proposal nao trouxe um site resolvido.",
                requires_human_approval=True,
                can_auto_execute=False,
                escalation_target="site-operations",
                approver_role_slugs=list(policy.approver_role_slugs),
                explainability_payload=explainability,
            )
        if classification.risk_level == AgentDecision.RiskLevel.CRITICAL and policy.autonomy_level < DecisionPolicy.AutonomyLevel.LEVEL_3:
            return PolicyEvaluationResult(
                policy=policy,
                outcome=AgentDecision.DecisionStatus.ESCALATED,
                reason="Acao classificada como critica; escalonamento obrigatorio antes de qualquer execucao.",
                requires_human_approval=True,
                can_auto_execute=False,
                escalation_target="executive-approval",
                approver_role_slugs=list(policy.approver_role_slugs),
                explainability_payload=explainability,
            )
        requires_human_approval = policy.requires_human_approval or classification.requires_human_approval
        can_auto_execute = bool(policy.config.get("auto_execute")) and classification.can_auto_execute and not requires_human_approval
        if can_auto_execute:
            outcome = AgentDecision.DecisionStatus.AUTO_APPROVED
            reason = f"Policy {policy.slug} permite autoexecucao segura para {classification.normalized_action_type}."
        elif requires_human_approval:
            outcome = AgentDecision.DecisionStatus.AWAITING_APPROVAL
            reason = f"Policy {policy.slug} exige aprovacao humana para {classification.normalized_action_type}."
        else:
            outcome = AgentDecision.DecisionStatus.APPROVED
            reason = f"Policy {policy.slug} aprovou materializacao controlada sem aprovacao adicional."
        return PolicyEvaluationResult(
            policy=policy,
            outcome=outcome,
            reason=reason,
            requires_human_approval=requires_human_approval,
            can_auto_execute=can_auto_execute,
            escalation_target="",
            approver_role_slugs=list(policy.approver_role_slugs),
            explainability_payload=explainability,
        )

    @staticmethod
    def get_user_role_slugs(*, user, company=None) -> set[str]:
        queryset = UserRoleAssignment.objects.filter(user=user, is_active=True, role__is_active=True).select_related("role")
        if company is not None:
            queryset = queryset.filter(models.Q(company=company) | models.Q(company__isnull=True))
        return {assignment.role.slug for assignment in queryset if assignment.is_current}
