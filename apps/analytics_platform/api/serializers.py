from rest_framework import serializers

from ..models import (
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
from ..services.analytics_service import AnalyticsEventService, AnalyticsMetricService


class AnalyticsEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsEvent
        fields = (
            "public_id",
            "event_type",
            "source_module",
            "entity_type",
            "entity_id",
            "user",
            "company",
            "payload",
            "occurred_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def create(self, validated_data):
        return AnalyticsEventService.record_event(**validated_data)


class AnalyticsMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsMetric
        fields = (
            "public_id",
            "metric_name",
            "metric_slug",
            "metric_type",
            "description",
            "unit",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "metric_slug", "created_at", "updated_at")


class AnalyticsDimensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsDimension
        fields = ("public_id", "name", "slug", "description", "is_active", "created_at", "updated_at")
        read_only_fields = ("public_id", "slug", "created_at", "updated_at")


class AnalyticsMetricValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsMetricValue
        fields = (
            "public_id",
            "metric",
            "dimension",
            "dimension_value",
            "value",
            "calculated_at",
            "reference_date",
            "source_module",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")

    def create(self, validated_data):
        return AnalyticsMetricService.record_metric_value(**validated_data)


class AnalyticsReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsReport
        fields = ("public_id", "name", "slug", "description", "report_type", "config_json", "is_active", "created_at", "updated_at")
        read_only_fields = ("public_id", "slug", "created_at", "updated_at")


class AnalyticsWidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsWidget
        fields = (
            "public_id",
            "dashboard",
            "widget_type",
            "title",
            "metric",
            "config_json",
            "ordering",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class AnalyticsDashboardSerializer(serializers.ModelSerializer):
    widgets = AnalyticsWidgetSerializer(many=True, read_only=True)

    class Meta:
        model = AnalyticsDashboard
        fields = ("public_id", "name", "slug", "description", "layout_config", "is_active", "widgets", "created_at", "updated_at")
        read_only_fields = ("public_id", "slug", "created_at", "updated_at")


class AnalyticsSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsSnapshot
        fields = ("public_id", "snapshot_type", "snapshot_date", "data_json", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class OperationalMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperationalMetrics
        fields = (
            "public_id",
            "company",
            "period_type",
            "period_start",
            "period_end",
            "total_work_orders",
            "total_preventives",
            "total_correctives",
            "total_revenue",
            "total_cost",
            "total_profit",
            "avg_response_time",
            "avg_execution_time",
            "sla_compliance_rate",
            "total_sla_compliant",
            "total_sla_violated",
            "metadata",
            "calculated_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "created_at", "updated_at")


class ClientProfitabilitySerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.display_name", read_only=True)

    class Meta:
        model = ClientProfitability
        fields = (
            "public_id",
            "company",
            "client",
            "client_name",
            "period_type",
            "period_start",
            "period_end",
            "revenue",
            "cost",
            "profit",
            "margin",
            "total_work_orders",
            "total_assets",
            "metadata",
            "calculated_at",
        )
        read_only_fields = fields


class ContractProfitabilitySerializer(serializers.ModelSerializer):
    contract_number = serializers.CharField(source="contract.contract_number", read_only=True)
    client_name = serializers.CharField(source="contract.client.display_name", read_only=True)

    class Meta:
        model = ContractProfitability
        fields = (
            "public_id",
            "company",
            "contract",
            "contract_number",
            "client_name",
            "period_type",
            "period_start",
            "period_end",
            "revenue",
            "cost",
            "profit",
            "margin",
            "total_work_orders",
            "total_assets",
            "metadata",
            "calculated_at",
        )
        read_only_fields = fields


class TechnicianPerformanceSerializer(serializers.ModelSerializer):
    technician_name = serializers.SerializerMethodField()

    class Meta:
        model = TechnicianPerformance
        fields = (
            "public_id",
            "company",
            "technician",
            "technician_name",
            "period_type",
            "period_start",
            "period_end",
            "jobs_completed",
            "jobs_in_progress",
            "avg_execution_time",
            "customer_rating",
            "profit_generated",
            "total_labor_minutes",
            "total_response_minutes",
            "metadata",
            "calculated_at",
        )
        read_only_fields = fields

    def get_technician_name(self, obj):
        return obj.technician.display_name or obj.technician.full_name or obj.technician.email


class AnalyticsRevenuePointSerializer(serializers.Serializer):
    label = serializers.CharField()
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2)


class AnalyticsProfitPointSerializer(serializers.Serializer):
    label = serializers.CharField()
    profit = serializers.DecimalField(max_digits=14, decimal_places=2)
    cost = serializers.DecimalField(max_digits=14, decimal_places=2)


class AnalyticsAssetEntrySerializer(serializers.Serializer):
    asset_id = serializers.UUIDField()
    asset_tag = serializers.CharField()
    asset_name = serializers.CharField()
    site_name = serializers.CharField()
    failure_count = serializers.IntegerField()
    maintenance_cost = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_orders = serializers.IntegerField()


class AnalyticsKpiSerializer(serializers.Serializer):
    label = serializers.CharField()
    value = serializers.DecimalField(max_digits=14, decimal_places=2)
    tone = serializers.CharField()
    helper = serializers.CharField()


class AnalyticsSlaSummarySerializer(serializers.Serializer):
    compliant = serializers.IntegerField()
    violated = serializers.IntegerField()
    compliance_rate = serializers.DecimalField(max_digits=7, decimal_places=2)
    avg_response_time = serializers.DecimalField(max_digits=12, decimal_places=2)
    avg_execution_time = serializers.DecimalField(max_digits=12, decimal_places=2)
    overdue_preventives = serializers.IntegerField()
