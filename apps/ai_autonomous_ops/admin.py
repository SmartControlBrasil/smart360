from django.contrib import admin

from .models import AutonomousAuditTrail, AutonomousExecution, AutonomousExecutionGuard, AutonomousIncident, AutonomousModeConfig


@admin.register(AutonomousModeConfig)
class AutonomousModeConfigAdmin(admin.ModelAdmin):
    list_display = ("company", "is_enabled", "mode_level", "max_risk_level", "kill_switch_enabled", "updated_at")
    list_filter = ("is_enabled", "mode_level", "max_risk_level", "kill_switch_enabled")
    search_fields = ("company__name",)


@admin.register(AutonomousExecutionGuard)
class AutonomousExecutionGuardAdmin(admin.ModelAdmin):
    list_display = ("company", "guard_type", "threshold_key", "threshold_value", "enabled")
    list_filter = ("guard_type", "enabled")


@admin.register(AutonomousExecution)
class AutonomousExecutionAdmin(admin.ModelAdmin):
    list_display = ("action_type", "company", "site", "source_agent", "risk_level", "confidence_score", "execution_status", "rollback_status", "created_at")
    list_filter = ("execution_status", "rollback_status", "risk_level", "source_agent")
    search_fields = ("action_type", "source_agent", "execution_summary")


@admin.register(AutonomousIncident)
class AutonomousIncidentAdmin(admin.ModelAdmin):
    list_display = ("incident_type", "company", "site", "severity", "status", "created_at")
    list_filter = ("severity", "status", "incident_type")


@admin.register(AutonomousAuditTrail)
class AutonomousAuditTrailAdmin(admin.ModelAdmin):
    list_display = ("autonomous_execution", "event_type", "actor_user", "created_at")
    list_filter = ("event_type",)

