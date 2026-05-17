from apps.ai_policy_studio.models import PolicyVersion


class PolicyVersioningService:
    @staticmethod
    def snapshot_policy(policy):
        return {
            "policy": {
                "slug": policy.slug,
                "name": policy.name,
                "description": policy.description,
                "tenant_scope": policy.tenant_scope,
                "is_global": policy.is_global,
                "status": policy.status,
                "version": policy.version,
            },
            "scopes": [
                {
                    "company_id": scope.company_id,
                    "site_id": scope.site_id,
                    "module_slug": scope.module_slug,
                    "action_type": scope.action_type,
                    "agent_slug": scope.agent_slug,
                    "copilot_key": scope.copilot_key,
                    "priority": scope.priority,
                }
                for scope in policy.scopes.all()
            ],
            "rules": [
                {
                    "action_type": rule.action_type,
                    "risk_level": rule.risk_level,
                    "autonomy_level": rule.autonomy_level,
                    "requires_approval": rule.requires_approval,
                    "allowed": rule.allowed,
                    "result": rule.result,
                    "approver_roles": rule.approver_roles,
                    "conditions": rule.conditions,
                    "rationale": rule.rationale,
                }
                for rule in policy.rules.all()
            ],
        }

    @classmethod
    def create_version(cls, *, policy, created_by_user=None, change_summary=""):
        version_number = (policy.versions.order_by("-version_number").values_list("version_number", flat=True).first() or 0) + 1
        PolicyVersion.objects.create(
            policy=policy,
            version_number=version_number,
            snapshot=cls.snapshot_policy(policy),
            change_summary=change_summary,
            created_by_user=created_by_user,
        )
        policy.version = version_number
        policy.save(update_fields=["version", "updated_at"])
        return version_number

