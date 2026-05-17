from django.contrib import admin

from .models import AgentDecision, DecisionApproval, DecisionAuditTrail, DecisionExecution, DecisionPolicy


class DecisionApprovalInline(admin.TabularInline):
    model = DecisionApproval
    extra = 0
    readonly_fields = ("public_id", "approval_status", "approver_user", "approved_at", "created_at", "updated_at")


class DecisionExecutionInline(admin.TabularInline):
    model = DecisionExecution
    extra = 0
    readonly_fields = (
        "public_id",
        "execution_status",
        "executed_by_mode",
        "executed_by_user",
        "executed_at",
        "finished_at",
        "duration_ms",
        "rollback_supported",
        "rollback_status",
        "created_at",
        "updated_at",
    )


class DecisionAuditInline(admin.TabularInline):
    model = DecisionAuditTrail
    extra = 0
    readonly_fields = ("public_id", "event_type", "actor_mode", "actor_label", "actor_user", "message", "metadata", "occurred_at")


@admin.register(DecisionPolicy)
class DecisionPolicyAdmin(admin.ModelAdmin):
    list_display = (
        "slug",
        "action_type",
        "risk_level",
        "autonomy_level",
        "requires_human_approval",
        "enabled",
        "tenant_scope_mode",
        "updated_at",
    )
    list_filter = ("risk_level", "autonomy_level", "requires_human_approval", "enabled", "tenant_scope_mode")
    search_fields = ("slug", "name", "action_type", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(AgentDecision)
class AgentDecisionAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "normalized_action_type",
        "company",
        "site",
        "risk_level",
        "decision_status",
        "policy_applied",
        "created_at",
    )
    list_filter = ("decision_status", "risk_level", "normalized_action_type", "company", "site")
    search_fields = ("public_id", "action_type", "normalized_action_type", "target_entity_id", "decision_reason")
    readonly_fields = ("public_id", "created_at", "updated_at", "decided_at")
    inlines = [DecisionApprovalInline, DecisionExecutionInline, DecisionAuditInline]


@admin.register(DecisionExecution)
class DecisionExecutionAdmin(admin.ModelAdmin):
    list_display = ("public_id", "decision", "execution_status", "executed_by_mode", "executed_at", "duration_ms")
    list_filter = ("execution_status", "executed_by_mode", "rollback_supported", "rollback_status")
    search_fields = ("public_id", "decision__public_id", "execution_summary", "error_message")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(DecisionApproval)
class DecisionApprovalAdmin(admin.ModelAdmin):
    list_display = ("public_id", "decision", "approval_status", "approver_user", "approved_at", "created_at")
    list_filter = ("approval_status",)
    search_fields = ("public_id", "decision__public_id", "comment", "approver_user__email")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(DecisionAuditTrail)
class DecisionAuditTrailAdmin(admin.ModelAdmin):
    list_display = ("public_id", "decision", "event_type", "actor_mode", "actor_label", "occurred_at")
    list_filter = ("event_type", "actor_mode")
    search_fields = ("public_id", "decision__public_id", "message", "actor_label")
    readonly_fields = ("public_id", "created_at")

