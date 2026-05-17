from apps.ai_policy_studio.models import PolicyEvaluation
from apps.observability_center.services.observability_service import SystemEventService


class PolicyAuditService:
    @staticmethod
    def log_evaluation(*, policy=None, rule=None, company=None, site=None, module_slug="", action_type="", result="", reason="", context_payload=None):
        evaluation = PolicyEvaluation.objects.create(
            policy=policy,
            rule=rule,
            company=company,
            site=site,
            module_slug=module_slug,
            action_type=action_type,
            result=result,
            reason=reason,
            context_payload=context_payload or {},
        )
        SystemEventService.log_system_event(
            event_type="policy.evaluated",
            source_module="ai_policy_studio",
            message=reason or "Policy evaluated.",
            entity_type=module_slug or "policy",
            entity_id=action_type or str(getattr(policy, "public_id", "")),
            company=company,
            site=site,
            payload={
                "policy_slug": getattr(policy, "slug", ""),
                "result": result,
                "rule_public_id": str(rule.public_id) if rule else "",
                "context": context_payload or {},
            },
        )
        if result == "deny":
            SystemEventService.log_system_event(
                event_type="policy.denied",
                source_module="ai_policy_studio",
                message=reason or "Policy denied action.",
                entity_type=module_slug or "policy",
                entity_id=action_type or str(getattr(policy, "public_id", "")),
                company=company,
                site=site,
                payload={"policy_slug": getattr(policy, "slug", "")},
            )
        else:
            SystemEventService.log_system_event(
                event_type="policy.applied",
                source_module="ai_policy_studio",
                message=reason or "Policy applied.",
                entity_type=module_slug or "policy",
                entity_id=action_type or str(getattr(policy, "public_id", "")),
                company=company,
                site=site,
                payload={"policy_slug": getattr(policy, "slug", ""), "result": result},
            )
        return evaluation

