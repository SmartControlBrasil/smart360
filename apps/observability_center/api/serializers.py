from rest_framework import serializers

from ..models import ErrorIncident, JobExecutionTrace, MetricCounter, RequestTrace, SystemEventLog


class SystemEventLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemEventLog
        fields = "__all__"
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class ErrorIncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ErrorIncident
        fields = "__all__"
        read_only_fields = (
            "id",
            "public_id",
            "first_seen_at",
            "last_seen_at",
            "occurrences_count",
            "created_at",
            "updated_at",
        )


class MetricCounterSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetricCounter
        fields = "__all__"
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class JobExecutionTraceSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobExecutionTrace
        fields = "__all__"
        read_only_fields = ("id", "public_id", "duration_ms", "created_at", "updated_at")


class RequestTraceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestTrace
        fields = "__all__"
        read_only_fields = ("id", "public_id", "created_at")


class ComponentStatusSerializer(serializers.Serializer):
    status = serializers.CharField()
    engine = serializers.CharField(required=False, allow_blank=True)
    backend = serializers.CharField(required=False, allow_blank=True)
    broker_url = serializers.CharField(required=False, allow_blank=True)
    result_backend = serializers.CharField(required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)


class HealthSummarySerializer(serializers.Serializer):
    status = serializers.CharField()
    service = serializers.CharField()
    environment = serializers.CharField()
    version = serializers.CharField()
    checks = serializers.DictField(child=serializers.JSONField())


class ErrorSummarySerializer(serializers.Serializer):
    total_open = serializers.IntegerField()
    total_acknowledged = serializers.IntegerField()
    by_status_and_severity = serializers.ListField(child=serializers.DictField())


class MetricsSummarySerializer(serializers.Serializer):
    reference_date = serializers.DateField()
    modules = serializers.ListField(child=serializers.DictField())


class PlatformObservabilitySummarySerializer(serializers.Serializer):
    health = serializers.DictField()
    recent_errors = serializers.ListField(child=serializers.DictField())
    critical_events = serializers.ListField(child=serializers.DictField())
    latest_audits = serializers.ListField(child=serializers.DictField())
    recent_jobs = serializers.ListField(child=serializers.DictField())
    billing_risk = serializers.ListField(child=serializers.DictField())
