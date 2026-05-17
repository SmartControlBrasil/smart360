from __future__ import annotations

from apps.access_control_center.services.access_service import AccessControlService
from apps.billing.services.billing_service import BillingAccessService


class AgentPolicyService:
    @staticmethod
    def can_run_agent(*, user, company, agent_definition, trigger_type="manual"):
        if not agent_definition.enabled or agent_definition.status != agent_definition.Status.ACTIVE:
            return False, "Agent is disabled."
        policy = getattr(agent_definition, "execution_policy", None)
        if trigger_type == "scheduled" and policy and not policy.allow_scheduled_runs:
            return False, "Scheduled runs are disabled for this agent."
        if trigger_type in {"event", "scheduled"} and user is None:
            if company and policy and policy.enforce_billing_active:
                billing_context = BillingAccessService.get_company_billing_context(company)
                if not billing_context["access_allowed"]:
                    return False, f"Billing blocked: {billing_context['access_status']}"
            return True, "System trigger allowed."
        allowed, reason = AccessControlService.check_permission(
            user=user,
            domain_slug="ai_agents_admin",
            action_slug="manage" if trigger_type in {"manual", "api"} else "view",
            company=company,
            module_name="ai_agents_center",
            resource_type="agent",
            resource_id=agent_definition.slug,
            log_decision=False,
        )
        if not allowed:
            return False, reason
        if company and policy and policy.enforce_billing_active:
            billing_context = BillingAccessService.get_company_billing_context(company)
            if not billing_context["access_allowed"]:
                return False, f"Billing blocked: {billing_context['access_status']}"
        return True, "Agent run allowed."

    @staticmethod
    def can_approve_proposal(*, user, company, proposal):
        return AccessControlService.check_permission(
            user=user,
            domain_slug="ai_agents_admin",
            action_slug="approve",
            company=company,
            module_name="ai_agents_center",
            resource_type=proposal.target_entity,
            resource_id=proposal.target_entity_id,
            log_decision=False,
        )
