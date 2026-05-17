from rest_framework import serializers

from apps.ai_simulation_engine.models import SimulationResult, SimulationRun, SimulationScenario, SimulationType


class SimulationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimulationType
        fields = ("public_id", "slug", "name", "description", "enabled", "policy_mode", "heuristics_config", "created_at", "updated_at")


class SimulationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimulationResult
        fields = (
            "public_id",
            "summary",
            "impact_score",
            "confidence_level",
            "risk_delta",
            "cost_delta",
            "sla_delta",
            "profit_delta",
            "travel_delta",
            "workload_delta",
            "recommendation",
            "result_payload",
            "created_at",
            "updated_at",
        )


class SimulationRunSerializer(serializers.ModelSerializer):
    result = SimulationResultSerializer(read_only=True)
    simulation_type = serializers.CharField(source="scenario.simulation_type.slug", read_only=True)
    scenario_title = serializers.CharField(source="scenario.title", read_only=True)

    class Meta:
        model = SimulationRun
        fields = (
            "public_id",
            "simulation_type",
            "scenario_title",
            "decision",
            "trigger_type",
            "source_type",
            "source_reference",
            "input_payload",
            "baseline_snapshot",
            "status",
            "started_at",
            "finished_at",
            "request_id",
            "created_by_user",
            "created_at",
            "updated_at",
            "result",
        )


class SimulationScenarioSerializer(serializers.ModelSerializer):
    runs = SimulationRunSerializer(many=True, read_only=True)
    simulation_type = SimulationTypeSerializer(read_only=True)

    class Meta:
        model = SimulationScenario
        fields = (
            "public_id",
            "simulation_type",
            "company",
            "site",
            "title",
            "description",
            "target_entity",
            "target_entity_id",
            "status",
            "created_by_user",
            "created_at",
            "updated_at",
            "runs",
        )


class SimulationRequestSerializer(serializers.Serializer):
    simulation_type = serializers.SlugField(required=False)
    decision_public_id = serializers.UUIDField(required=False)
    company = serializers.PrimaryKeyRelatedField(read_only=True)
    site = serializers.PrimaryKeyRelatedField(read_only=True)
    title = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    target_entity = serializers.CharField(required=False, allow_blank=True)
    target_entity_id = serializers.CharField(required=False, allow_blank=True)
    input_payload = serializers.JSONField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.companies.models import Company
        from apps.smart_system.models import OperationalSite

        self.fields["company"].queryset = Company.objects.all()
        self.fields["site"].queryset = OperationalSite.objects.all()

    def validate(self, attrs):
        if not attrs.get("decision_public_id") and not attrs.get("simulation_type"):
            raise serializers.ValidationError("Provide either decision_public_id or simulation_type.")
        return attrs
