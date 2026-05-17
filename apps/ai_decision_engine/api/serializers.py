from rest_framework import serializers

from apps.ai_decision_engine.models import AgentDecision, DecisionApproval, DecisionAuditTrail, DecisionExecution, DecisionPolicy


class DecisionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = DecisionPolicy
        fields = (
            "public_id",
            "slug",
            "name",
            "description",
            "action_type",
            "risk_level",
            "autonomy_level",
            "requires_human_approval",
            "enabled",
            "tenant_scope_mode",
            "approver_role_slugs",
            "config",
            "created_at",
            "updated_at",
        )


class DecisionApprovalSerializer(serializers.ModelSerializer):
    approver_email = serializers.SerializerMethodField()

    class Meta:
        model = DecisionApproval
        fields = (
            "public_id",
            "approval_status",
            "approver_user",
            "approver_email",
            "requested_role_slugs",
            "comment",
            "approved_at",
            "expires_at",
            "created_at",
            "updated_at",
        )

    def get_approver_email(self, obj):
        return getattr(obj.approver_user, "email", "")


class DecisionExecutionSerializer(serializers.ModelSerializer):
    executed_by_email = serializers.SerializerMethodField()

    class Meta:
        model = DecisionExecution
        fields = (
            "public_id",
            "execution_status",
            "execution_summary",
            "executed_by_mode",
            "executed_by_user",
            "executed_by_email",
            "executed_at",
            "finished_at",
            "duration_ms",
            "rollback_supported",
            "rollback_status",
            "rollback_reason",
            "result_payload",
            "error_message",
            "created_at",
            "updated_at",
        )

    def get_executed_by_email(self, obj):
        return getattr(obj.executed_by_user, "email", "")


class DecisionAuditTrailSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()

    class Meta:
        model = DecisionAuditTrail
        fields = (
            "public_id",
            "event_type",
            "actor_mode",
            "actor_label",
            "actor_user",
            "actor_email",
            "message",
            "metadata",
            "occurred_at",
        )

    def get_actor_email(self, obj):
        return getattr(obj.actor_user, "email", "")


class AgentDecisionSerializer(serializers.ModelSerializer):
    policy_applied = DecisionPolicySerializer(read_only=True)
    approvals = DecisionApprovalSerializer(many=True, read_only=True)
    executions = DecisionExecutionSerializer(many=True, read_only=True)
    audit_entries = DecisionAuditTrailSerializer(many=True, read_only=True)
    proposal_public_id = serializers.UUIDField(source="agent_action_proposal.public_id", read_only=True)
    agent_slug = serializers.CharField(source="agent_action_proposal.agent_run.agent.slug", read_only=True)
    proposal_title = serializers.CharField(source="agent_action_proposal.title", read_only=True)
    proposal_summary = serializers.CharField(source="agent_action_proposal.summary", read_only=True)

    class Meta:
        model = AgentDecision
        fields = (
            "public_id",
            "proposal_public_id",
            "agent_slug",
            "proposal_title",
            "proposal_summary",
            "company",
            "site",
            "action_type",
            "normalized_action_type",
            "target_entity",
            "target_entity_id",
            "risk_level",
            "autonomy_level",
            "tenant_scope_mode",
            "requires_human_approval",
            "can_auto_execute",
            "rollback_required",
            "decision_status",
            "decision_reason",
            "policy_applied",
            "decided_by_user",
            "decided_at",
            "explainability_payload",
            "execution_payload",
            "escalation_target",
            "approvals",
            "executions",
            "audit_entries",
            "created_at",
            "updated_at",
        )


class DecisionApprovalCommandSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True)

