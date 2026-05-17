from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Q

from apps.ai_policy_studio.models import Policy, PolicyRule, PolicyScope

from .audit import PolicyAuditService


@dataclass(frozen=True)
class PolicyEngineResult:
    policy: Policy | None
    rule: PolicyRule | None
    result: str
    reason: str
    requires_approval: bool
    allowed: bool
    approver_roles: list[str]
    autonomy_level: int
    matched_scope: dict


class PolicyStudioEngine:
    @staticmethod
    def _specificity(scope: PolicyScope, *, company=None, site=None, module_slug="", action_type="", agent_slug="", copilot_key=""):
        score = 0
        if scope.company_id and company and scope.company_id == company.id:
            score += 10
        if scope.site_id and site and scope.site_id == site.id:
            score += 10
        if scope.module_slug and scope.module_slug == module_slug:
            score += 6
        if scope.action_type and scope.action_type == action_type:
            score += 6
        if scope.agent_slug and scope.agent_slug == agent_slug:
            score += 4
        if scope.copilot_key and scope.copilot_key == copilot_key:
            score += 4
        return score - scope.priority

    @staticmethod
    def _conditions_match(rule: PolicyRule, context: dict):
        conditions = rule.conditions or {}
        for key, expected in conditions.items():
            if context.get(key) != expected:
                return False
        return True

    @staticmethod
    def _rule_specificity(rule: PolicyRule, *, action_type="", risk_level="any"):
        score = 0
        if rule.action_type and rule.action_type == action_type:
            score += 10
        if rule.risk_level and rule.risk_level not in {"", PolicyRule.RiskLevel.ANY} and rule.risk_level == risk_level:
            score += 6
        return score

    @classmethod
    def _matching_scopes(cls, *, company=None, site=None, module_slug="", action_type="", agent_slug="", copilot_key=""):
        queryset = PolicyScope.objects.select_related("policy", "company", "site").filter(policy__status=Policy.Status.ACTIVE)
        queryset = queryset.filter(Q(company=company) | Q(company__isnull=True))
        queryset = queryset.filter(Q(site=site) | Q(site__isnull=True))
        queryset = queryset.filter(Q(module_slug=module_slug) | Q(module_slug=""))
        queryset = queryset.filter(Q(action_type=action_type) | Q(action_type=""))
        queryset = queryset.filter(Q(agent_slug=agent_slug) | Q(agent_slug=""))
        queryset = queryset.filter(Q(copilot_key=copilot_key) | Q(copilot_key=""))
        return sorted(
            queryset,
            key=lambda scope: cls._specificity(
                scope,
                company=company,
                site=site,
                module_slug=module_slug,
                action_type=action_type,
                agent_slug=agent_slug,
                copilot_key=copilot_key,
            ),
            reverse=True,
        )

    @classmethod
    def evaluate(
        cls,
        *,
        module_slug,
        action_type,
        company=None,
        site=None,
        risk_level="any",
        autonomy_level=0,
        agent_slug="",
        copilot_key="",
        context=None,
    ) -> PolicyEngineResult:
        context = context or {}
        scopes = cls._matching_scopes(
            company=company,
            site=site,
            module_slug=module_slug,
            action_type=action_type,
            agent_slug=agent_slug,
            copilot_key=copilot_key,
        )
        for scope in scopes:
            rules = scope.policy.rules.filter(Q(action_type=action_type) | Q(action_type=""))
            if risk_level:
                rules = rules.filter(Q(risk_level=risk_level) | Q(risk_level=PolicyRule.RiskLevel.ANY))
            for rule in sorted(rules, key=lambda item: cls._rule_specificity(item, action_type=action_type, risk_level=risk_level), reverse=True):
                if not cls._conditions_match(rule, context):
                    continue
                reason = rule.rationale or f"Policy {scope.policy.slug} matched for {module_slug}:{action_type}."
                PolicyAuditService.log_evaluation(
                    policy=scope.policy,
                    rule=rule,
                    company=company,
                    site=site,
                    module_slug=module_slug,
                    action_type=action_type,
                    result=rule.result,
                    reason=reason,
                    context_payload={
                        "risk_level": risk_level,
                        "autonomy_level": autonomy_level,
                        "agent_slug": agent_slug,
                        "copilot_key": copilot_key,
                        **context,
                    },
                )
                return PolicyEngineResult(
                    policy=scope.policy,
                    rule=rule,
                    result=rule.result,
                    reason=reason,
                    requires_approval=rule.requires_approval or rule.result == PolicyRule.EvaluationResult.REQUIRE_APPROVAL,
                    allowed=rule.allowed and rule.result != PolicyRule.EvaluationResult.DENY,
                    approver_roles=list(rule.approver_roles),
                    autonomy_level=rule.autonomy_level,
                    matched_scope={
                        "scope_public_id": str(scope.public_id),
                        "company_id": scope.company_id,
                        "site_id": scope.site_id,
                        "module_slug": scope.module_slug,
                        "action_type": scope.action_type,
                    },
                )
        reason = f"No active Policy Studio rule matched for {module_slug}:{action_type}."
        PolicyAuditService.log_evaluation(
            policy=None,
            rule=None,
            company=company,
            site=site,
            module_slug=module_slug,
            action_type=action_type,
            result="deny",
            reason=reason,
            context_payload={"risk_level": risk_level, "autonomy_level": autonomy_level, **context},
        )
        return PolicyEngineResult(
            policy=None,
            rule=None,
            result=PolicyRule.EvaluationResult.DENY,
            reason=reason,
            requires_approval=False,
            allowed=False,
            approver_roles=[],
            autonomy_level=0,
            matched_scope={},
        )
