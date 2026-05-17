from rest_framework import serializers

from apps.ai_optimization_loop.models import (
    DecisionOutcome,
    FeedbackSignal,
    OptimizationPolicy,
    OptimizationProposal,
    RecommendationOutcome,
    SimulationOutcome,
)


class FeedbackSignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackSignal
        fields = (
            "public_id",
            "source_type",
            "source_reference",
            "company",
            "site",
            "user",
            "signal_type",
            "score",
            "comment",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "user", "created_at", "updated_at")


class RecommendationOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationOutcome
        fields = "__all__"


class DecisionOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DecisionOutcome
        fields = "__all__"


class SimulationOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SimulationOutcome
        fields = "__all__"


class OptimizationPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizationPolicy
        fields = "__all__"


class OptimizationProposalSerializer(serializers.ModelSerializer):
    policy_applied = OptimizationPolicySerializer(read_only=True)

    class Meta:
        model = OptimizationProposal
        fields = "__all__"


class OptimizationProposalDecisionSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True)
    apply = serializers.BooleanField(required=False, default=True)
