from django.contrib import admin

from .models import (
    DecisionOutcome,
    FeedbackSignal,
    OptimizationAuditTrail,
    OptimizationPolicy,
    OptimizationProposal,
    RecommendationOutcome,
    SimulationOutcome,
)


@admin.register(RecommendationOutcome)
class RecommendationOutcomeAdmin(admin.ModelAdmin):
    list_display = ("recommendation", "company", "site", "outcome_status", "effectiveness_level", "effectiveness_score", "measured_at")
    list_filter = ("outcome_status", "effectiveness_level", "company", "site")
    search_fields = ("recommendation__title", "recommendation__entity_id", "observed_effect_summary")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(DecisionOutcome)
class DecisionOutcomeAdmin(admin.ModelAdmin):
    list_display = ("decision", "company", "site", "result_status", "effectiveness_level", "effectiveness_score", "measured_at")
    list_filter = ("result_status", "effectiveness_level", "company", "site")
    search_fields = ("decision__normalized_action_type", "decision__target_entity_id", "evaluation_summary")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(SimulationOutcome)
class SimulationOutcomeAdmin(admin.ModelAdmin):
    list_display = ("simulation_run", "company", "site", "result_status", "effectiveness_level", "effectiveness_score", "measured_at")
    list_filter = ("result_status", "effectiveness_level", "company", "site")
    search_fields = ("simulation_run__scenario__title", "evaluation_summary")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(FeedbackSignal)
class FeedbackSignalAdmin(admin.ModelAdmin):
    list_display = ("source_type", "source_reference", "signal_type", "score", "company", "site", "user", "created_at")
    list_filter = ("source_type", "signal_type", "company", "site")
    search_fields = ("source_reference", "comment")
    readonly_fields = ("public_id", "created_at", "updated_at")


class OptimizationAuditInline(admin.TabularInline):
    model = OptimizationAuditTrail
    extra = 0
    readonly_fields = ("public_id", "actor_user", "event_type", "message", "payload", "created_at")


@admin.register(OptimizationPolicy)
class OptimizationPolicyAdmin(admin.ModelAdmin):
    list_display = ("slug", "target_type", "proposal_type", "risk_level", "requires_human_approval", "auto_apply_on_approval", "enabled")
    list_filter = ("target_type", "proposal_type", "risk_level", "requires_human_approval", "enabled")
    search_fields = ("slug", "name", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(OptimizationProposal)
class OptimizationProposalAdmin(admin.ModelAdmin):
    list_display = ("public_id", "target_type", "proposal_type", "risk_level", "status", "company", "approved_by_user", "applied_at")
    list_filter = ("target_type", "proposal_type", "risk_level", "status", "company", "site")
    search_fields = ("target_reference", "rationale", "evidence_summary")
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = [OptimizationAuditInline]
