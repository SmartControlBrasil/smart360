from django.contrib import admin

from .models import Policy, PolicyEvaluation, PolicyRule, PolicyScope, PolicySimulationRun, PolicyVersion


class PolicyScopeInline(admin.TabularInline):
    model = PolicyScope
    extra = 0
    readonly_fields = ("public_id", "created_at")


class PolicyRuleInline(admin.TabularInline):
    model = PolicyRule
    extra = 0
    readonly_fields = ("public_id", "created_at", "updated_at")


class PolicyVersionInline(admin.TabularInline):
    model = PolicyVersion
    extra = 0
    readonly_fields = ("public_id", "version_number", "snapshot", "change_summary", "created_by_user", "created_at")


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "tenant_scope", "is_global", "status", "version", "updated_at")
    list_filter = ("tenant_scope", "is_global", "status")
    search_fields = ("slug", "name", "description")
    readonly_fields = ("public_id", "version", "created_at", "updated_at")
    inlines = [PolicyScopeInline, PolicyRuleInline, PolicyVersionInline]


@admin.register(PolicyEvaluation)
class PolicyEvaluationAdmin(admin.ModelAdmin):
    list_display = ("module_slug", "action_type", "result", "policy", "company", "site", "evaluated_at")
    list_filter = ("module_slug", "result", "company", "site")
    search_fields = ("action_type", "reason")
    readonly_fields = ("public_id", "evaluated_at")


@admin.register(PolicySimulationRun)
class PolicySimulationRunAdmin(admin.ModelAdmin):
    list_display = ("policy", "company", "site", "created_by_user", "created_at")
    list_filter = ("policy", "company", "site")
    readonly_fields = ("public_id", "input_payload", "result_payload", "created_at")
