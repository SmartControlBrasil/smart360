from django.contrib import admin

from .models import Experiment, ExperimentAssignment, ExperimentAuditTrail, ExperimentMetric, ExperimentResult, Variant


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 0


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "target_component",
        "target_reference",
        "status",
        "primary_metric",
        "auto_promote",
        "company",
        "site",
        "start_date",
    )
    list_filter = ("target_component", "status", "auto_promote", "company", "site")
    search_fields = ("name", "slug", "target_reference")
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = [VariantInline]


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ("name", "experiment", "weight", "enabled", "is_control", "created_at")
    list_filter = ("enabled", "is_control", "experiment__target_component")
    search_fields = ("name", "slug", "experiment__name", "experiment__slug")


@admin.register(ExperimentAssignment)
class ExperimentAssignmentAdmin(admin.ModelAdmin):
    list_display = ("experiment", "variant", "entity_key", "entity_type", "company", "site", "assigned_at")
    list_filter = ("experiment", "variant", "company", "site")
    search_fields = ("entity_key", "entity_type", "experiment__name")
    readonly_fields = ("public_id", "assigned_at", "created_at", "updated_at")


@admin.register(ExperimentMetric)
class ExperimentMetricAdmin(admin.ModelAdmin):
    list_display = ("experiment", "variant", "metric_type", "value", "unit", "source_component", "recorded_at")
    list_filter = ("metric_type", "source_component", "experiment", "variant")
    search_fields = ("source_reference", "experiment__name")
    readonly_fields = ("public_id", "created_at")


@admin.register(ExperimentResult)
class ExperimentResultAdmin(admin.ModelAdmin):
    list_display = ("experiment", "winning_variant", "primary_metric", "confidence_level", "created_at")
    list_filter = ("confidence_level", "primary_metric")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(ExperimentAuditTrail)
class ExperimentAuditTrailAdmin(admin.ModelAdmin):
    list_display = ("experiment", "variant", "event_type", "actor_user", "created_at")
    list_filter = ("event_type", "experiment")
    search_fields = ("message", "experiment__name")
    readonly_fields = ("public_id", "created_at")

