from django.contrib import admin

from .models import SimulationAuditTrail, SimulationResult, SimulationRun, SimulationScenario, SimulationType


@admin.register(SimulationType)
class SimulationTypeAdmin(admin.ModelAdmin):
    list_display = ("slug", "policy_mode", "enabled", "updated_at")
    list_filter = ("policy_mode", "enabled")
    search_fields = ("slug", "name", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


class SimulationResultInline(admin.StackedInline):
    model = SimulationResult
    extra = 0
    readonly_fields = ("public_id", "created_at", "updated_at")


class SimulationAuditInline(admin.TabularInline):
    model = SimulationAuditTrail
    extra = 0
    readonly_fields = ("public_id", "event_type", "actor_user", "message", "payload", "created_at")


@admin.register(SimulationScenario)
class SimulationScenarioAdmin(admin.ModelAdmin):
    list_display = ("title", "simulation_type", "company", "site", "status", "created_by_user", "created_at")
    list_filter = ("simulation_type", "status", "company", "site")
    search_fields = ("title", "description", "target_entity_id")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(SimulationRun)
class SimulationRunAdmin(admin.ModelAdmin):
    list_display = ("public_id", "scenario", "decision", "trigger_type", "source_type", "status", "created_at")
    list_filter = ("trigger_type", "source_type", "status", "scenario__simulation_type")
    search_fields = ("public_id", "source_reference", "scenario__title")
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = [SimulationResultInline, SimulationAuditInline]


@admin.register(SimulationResult)
class SimulationResultAdmin(admin.ModelAdmin):
    list_display = ("public_id", "simulation_run", "impact_score", "confidence_level", "created_at")
    list_filter = ("confidence_level",)
    search_fields = ("summary", "recommendation")
    readonly_fields = ("public_id", "created_at", "updated_at")

