from rest_framework import serializers

from apps.ai_autonomous_ops.models import AutonomousExecution, AutonomousExecutionGuard, AutonomousIncident, AutonomousModeConfig


class AutonomousModeConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousModeConfig
        fields = "__all__"
        read_only_fields = ("public_id", "created_at", "updated_at")


class AutonomousExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousExecution
        fields = "__all__"


class AutonomousIncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousIncident
        fields = "__all__"


class AutonomousExecutionGuardSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutonomousExecutionGuard
        fields = "__all__"

