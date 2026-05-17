from django.contrib import admin

from .models import (
    AnalyticsDashboard,
    AnalyticsDimension,
    AnalyticsEvent,
    AnalyticsMetric,
    AnalyticsMetricValue,
    AnalyticsReport,
    AnalyticsSnapshot,
    AnalyticsWidget,
    ClientProfitability,
    ContractProfitability,
    OperationalMetrics,
    TechnicianPerformance,
)


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "source_module", "entity_type", "entity_id", "company", "occurred_at")
    list_filter = ("source_module", "event_type", "occurred_at")
    search_fields = ("event_type", "source_module", "entity_type", "entity_id", "user__email", "company__name")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("user", "company")


@admin.register(AnalyticsMetric)
class AnalyticsMetricAdmin(admin.ModelAdmin):
    list_display = ("metric_name", "metric_type", "unit", "is_active", "updated_at")
    list_filter = ("metric_type", "is_active")
    search_fields = ("metric_name", "metric_slug", "description", "unit")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(AnalyticsMetricValue)
class AnalyticsMetricValueAdmin(admin.ModelAdmin):
    list_display = ("metric", "dimension", "dimension_value", "value", "reference_date", "source_module")
    list_filter = ("metric", "dimension", "source_module", "reference_date")
    search_fields = ("metric__metric_name", "dimension__name", "dimension_value", "source_module")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("metric", "dimension")


@admin.register(AnalyticsDimension)
class AnalyticsDimensionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(AnalyticsReport)
class AnalyticsReportAdmin(admin.ModelAdmin):
    list_display = ("name", "report_type", "is_active", "updated_at")
    list_filter = ("report_type", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


class AnalyticsWidgetInline(admin.TabularInline):
    model = AnalyticsWidget
    extra = 0
    autocomplete_fields = ("metric",)
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(AnalyticsDashboard)
class AnalyticsDashboardAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = (AnalyticsWidgetInline,)


@admin.register(AnalyticsWidget)
class AnalyticsWidgetAdmin(admin.ModelAdmin):
    list_display = ("title", "dashboard", "widget_type", "metric", "ordering", "is_active")
    list_filter = ("widget_type", "is_active", "dashboard")
    search_fields = ("title", "dashboard__name", "metric__metric_name")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("dashboard", "metric")


@admin.register(AnalyticsSnapshot)
class AnalyticsSnapshotAdmin(admin.ModelAdmin):
    list_display = ("snapshot_type", "snapshot_date", "updated_at")
    list_filter = ("snapshot_type", "snapshot_date")
    search_fields = ("snapshot_type",)
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(OperationalMetrics)
class OperationalMetricsAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "period_type",
        "period_start",
        "total_work_orders",
        "total_revenue",
        "total_profit",
        "sla_compliance_rate",
    )
    list_filter = ("period_type", "company")
    search_fields = ("company__name",)
    readonly_fields = ("public_id", "created_at", "updated_at", "calculated_at")
    autocomplete_fields = ("company",)


@admin.register(ClientProfitability)
class ClientProfitabilityAdmin(admin.ModelAdmin):
    list_display = ("client", "period_type", "period_start", "revenue", "cost", "profit", "margin")
    list_filter = ("period_type", "company")
    search_fields = ("client__display_name", "company__name")
    readonly_fields = ("public_id", "created_at", "updated_at", "calculated_at")
    autocomplete_fields = ("company", "client")


@admin.register(ContractProfitability)
class ContractProfitabilityAdmin(admin.ModelAdmin):
    list_display = ("contract", "period_type", "period_start", "revenue", "cost", "profit", "margin")
    list_filter = ("period_type", "company")
    search_fields = ("contract__contract_number", "contract__client__display_name", "company__name")
    readonly_fields = ("public_id", "created_at", "updated_at", "calculated_at")
    autocomplete_fields = ("company", "contract")


@admin.register(TechnicianPerformance)
class TechnicianPerformanceAdmin(admin.ModelAdmin):
    list_display = (
        "technician",
        "company",
        "period_type",
        "period_start",
        "jobs_completed",
        "jobs_in_progress",
        "customer_rating",
        "profit_generated",
    )
    list_filter = ("period_type", "company")
    search_fields = ("technician__email", "technician__first_name", "company__name")
    readonly_fields = ("public_id", "created_at", "updated_at", "calculated_at")
    autocomplete_fields = ("company", "technician")
