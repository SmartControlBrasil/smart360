from rest_framework import serializers

from apps.ai_automation_center.models import (
    AIAnnotation,
    AIContextProfile,
    AIGeneratedArtifact,
    AIModelConfig,
    AITaskExecution,
    AITaskRequest,
    AITaskType,
    AutomationExecution,
    AutomationRule,
    PromptTemplate,
    PromptVersion,
    RetrievalSourceConfig,
)


class AITaskTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AITaskType
        fields = "__all__"
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class PromptTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptTemplate
        fields = "__all__"
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class PromptVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptVersion
        fields = "__all__"
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class AIContextProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIContextProfile
        fields = "__all__"
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class AIModelConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIModelConfig
        fields = "__all__"
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class AITaskRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = AITaskRequest
        fields = "__all__"
        read_only_fields = (
            "id",
            "public_id",
            "created_at",
            "updated_at",
            "started_at",
            "completed_at",
            "failed_at",
            "error_message",
        )


class AITaskExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AITaskExecution
        fields = "__all__"
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class AIGeneratedArtifactSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIGeneratedArtifact
        fields = "__all__"
        read_only_fields = ("id", "public_id", "created_at", "updated_at", "approved_at")


class AutomationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationRule
        fields = "__all__"
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class AutomationExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationExecution
        fields = "__all__"
        read_only_fields = ("id", "public_id", "created_at", "updated_at", "completed_at", "failed_at")


class AIAnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIAnnotation
        fields = "__all__"
        read_only_fields = ("id", "public_id", "created_at", "updated_at")


class RetrievalSourceConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = RetrievalSourceConfig
        fields = "__all__"
        read_only_fields = ("id", "public_id", "slug", "created_at", "updated_at")


class PromptPreviewSerializer(serializers.Serializer):
    prompt_template = serializers.PrimaryKeyRelatedField(queryset=PromptTemplate.objects.all())
    input_payload = serializers.JSONField(required=False)


class RunTaskSerializer(serializers.Serializer):
    task_type = serializers.PrimaryKeyRelatedField(queryset=AITaskType.objects.all())
    prompt_template = serializers.PrimaryKeyRelatedField(queryset=PromptTemplate.objects.all(), required=False, allow_null=True)
    context_profile = serializers.PrimaryKeyRelatedField(queryset=AIContextProfile.objects.all(), required=False, allow_null=True)
    source_module = serializers.CharField()
    source_reference_type = serializers.CharField(required=False, allow_blank=True)
    source_reference_id = serializers.CharField(required=False, allow_blank=True)
    input_payload = serializers.JSONField(required=False)
    priority = serializers.ChoiceField(choices=AITaskRequest.Priority.choices, required=False)
    model_name = serializers.CharField(required=False, allow_blank=True)

