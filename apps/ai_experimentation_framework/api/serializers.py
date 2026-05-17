from rest_framework import serializers

from apps.ai_experimentation_framework.models import Experiment, ExperimentAssignment, ExperimentMetric, ExperimentResult, Variant


class VariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variant
        fields = (
            "public_id",
            "name",
            "slug",
            "description",
            "config_payload",
            "weight",
            "enabled",
            "is_control",
            "created_at",
        )
        read_only_fields = ("public_id", "created_at")


class ExperimentResultSerializer(serializers.ModelSerializer):
    winning_variant = VariantSerializer(read_only=True)

    class Meta:
        model = ExperimentResult
        fields = ("public_id", "summary", "primary_metric", "confidence_level", "recommendation", "result_payload", "winning_variant")


class ExperimentSerializer(serializers.ModelSerializer):
    variants = VariantSerializer(many=True, read_only=True)
    result = ExperimentResultSerializer(read_only=True)
    winner_variant = VariantSerializer(read_only=True)

    class Meta:
        model = Experiment
        fields = (
            "public_id",
            "name",
            "slug",
            "description",
            "target_component",
            "target_reference",
            "status",
            "start_date",
            "end_date",
            "traffic_split",
            "assignment_strategy",
            "primary_metric",
            "success_direction",
            "min_sample_size",
            "min_runtime_hours",
            "auto_promote",
            "configuration_payload",
            "winner_variant",
            "company",
            "site",
            "variants",
            "result",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "public_id",
            "slug",
            "traffic_split",
            "winner_variant",
            "result",
            "created_at",
            "updated_at",
        )


class ExperimentCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=180)
    description = serializers.CharField(required=False, allow_blank=True)
    target_component = serializers.ChoiceField(choices=Experiment.TargetComponent.choices)
    target_reference = serializers.CharField(required=False, allow_blank=True)
    company = serializers.IntegerField(required=False)
    site = serializers.IntegerField(required=False)
    assignment_strategy = serializers.ChoiceField(choices=Experiment.AssignmentStrategy.choices, default=Experiment.AssignmentStrategy.WEIGHTED)
    primary_metric = serializers.CharField(required=False, default="effectiveness_score")
    success_direction = serializers.ChoiceField(choices=Experiment.SuccessDirection.choices, default=Experiment.SuccessDirection.HIGHER_IS_BETTER)
    min_sample_size = serializers.IntegerField(required=False, default=20)
    min_runtime_hours = serializers.IntegerField(required=False, default=24)
    auto_promote = serializers.BooleanField(required=False, default=False)
    configuration_payload = serializers.JSONField(required=False)
    variants = serializers.ListField(child=serializers.JSONField(), allow_empty=False)


class AssignmentRequestSerializer(serializers.Serializer):
    entity_key = serializers.CharField(max_length=180)
    entity_type = serializers.CharField(required=False, allow_blank=True)
    context = serializers.JSONField(required=False)


class ExperimentAssignmentSerializer(serializers.ModelSerializer):
    variant = VariantSerializer(read_only=True)

    class Meta:
        model = ExperimentAssignment
        fields = (
            "public_id",
            "entity_key",
            "entity_type",
            "assignment_reason",
            "context_payload",
            "assigned_at",
            "variant",
        )


class MetricRecordSerializer(serializers.Serializer):
    assignment_public_id = serializers.UUIDField()
    metric_type = serializers.CharField(max_length=80)
    value = serializers.DecimalField(max_digits=14, decimal_places=4)
    unit = serializers.CharField(required=False, allow_blank=True)
    source_component = serializers.CharField(required=False, allow_blank=True)
    source_reference = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class ExperimentMetricSerializer(serializers.ModelSerializer):
    variant = VariantSerializer(read_only=True)

    class Meta:
        model = ExperimentMetric
        fields = (
            "public_id",
            "metric_type",
            "value",
            "unit",
            "source_component",
            "source_reference",
            "metadata",
            "recorded_at",
            "variant",
        )
