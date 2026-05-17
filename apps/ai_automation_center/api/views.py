from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_automation_center.api.serializers import (
    AIAnnotationSerializer,
    AIContextProfileSerializer,
    AIGeneratedArtifactSerializer,
    AIModelConfigSerializer,
    AITaskExecutionSerializer,
    AITaskRequestSerializer,
    AITaskTypeSerializer,
    AutomationExecutionSerializer,
    AutomationRuleSerializer,
    PromptPreviewSerializer,
    PromptTemplateSerializer,
    PromptVersionSerializer,
    RetrievalSourceConfigSerializer,
    RunTaskSerializer,
)
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
from apps.ai_automation_center.services.ai_service import (
    AITaskService,
    AutomationService,
    PromptTemplateService,
)


class AIBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class AITaskTypeViewSet(AIBaseViewSet):
    queryset = AITaskType.objects.all()
    serializer_class = AITaskTypeSerializer
    filterset_fields = ("task_category", "is_active")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "created_at", "updated_at")


class PromptTemplateViewSet(AIBaseViewSet):
    queryset = PromptTemplate.objects.select_related("task_type", "created_by").all()
    serializer_class = PromptTemplateSerializer
    filterset_fields = ("task_type", "source_module", "is_active", "created_by")
    search_fields = ("name", "slug", "prompt_template", "model_hint")
    ordering_fields = ("name", "created_at", "updated_at")

    def perform_create(self, serializer):
        prompt = serializer.save(created_by=self.request.user)
        PromptTemplateService.create_version_snapshot(prompt)

    @action(detail=True, methods=["post"], url_path="preview")
    def preview(self, request, pk=None):
        prompt = self.get_object()
        preview = PromptTemplateService.render_preview(prompt, request.data.get("input_payload", {}))
        return Response({"preview": preview}, status=status.HTTP_200_OK)


class PromptVersionViewSet(AIBaseViewSet):
    queryset = PromptVersion.objects.select_related("prompt_template", "created_by").all()
    serializer_class = PromptVersionSerializer
    filterset_fields = ("prompt_template", "created_by")
    search_fields = ("prompt_template__name", "version_label", "notes")
    ordering_fields = ("created_at", "updated_at")


class AIContextProfileViewSet(AIBaseViewSet):
    queryset = AIContextProfile.objects.all()
    serializer_class = AIContextProfileSerializer
    filterset_fields = ("source_module", "is_active")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "created_at", "updated_at")


class AIModelConfigViewSet(AIBaseViewSet):
    queryset = AIModelConfig.objects.all()
    serializer_class = AIModelConfigSerializer
    filterset_fields = ("provider_name", "model_type", "is_active")
    search_fields = ("name", "slug", "model_identifier")
    ordering_fields = ("name", "created_at", "updated_at")


class AITaskRequestViewSet(AIBaseViewSet):
    queryset = AITaskRequest.objects.select_related(
        "task_type",
        "prompt_template",
        "context_profile",
        "requested_by",
    ).all()
    serializer_class = AITaskRequestSerializer
    filterset_fields = ("task_type", "source_module", "status", "priority", "requested_by")
    search_fields = ("source_reference_type", "source_reference_id", "error_message")
    ordering_fields = ("created_at", "started_at", "completed_at", "updated_at")

    def perform_create(self, serializer):
        serializer.save(requested_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="run")
    def run(self, request, pk=None):
        task_request = self.get_object()
        task_request, execution, artifact = AITaskService.run_task(task_request)
        return Response(
            {
                "task_request": AITaskRequestSerializer(task_request).data,
                "execution": AITaskExecutionSerializer(execution).data,
                "artifact": AIGeneratedArtifactSerializer(artifact).data,
            },
            status=status.HTTP_200_OK,
        )


class AITaskExecutionViewSet(AIBaseViewSet):
    queryset = AITaskExecution.objects.select_related("task_request").all()
    serializer_class = AITaskExecutionSerializer
    filterset_fields = ("task_request", "execution_mode", "provider_name", "status")
    search_fields = ("task_request__source_reference_id", "output_text", "error_message")
    ordering_fields = ("started_at", "completed_at", "updated_at")


class AIGeneratedArtifactViewSet(AIBaseViewSet):
    queryset = AIGeneratedArtifact.objects.select_related("task_execution", "approved_by", "related_file").all()
    serializer_class = AIGeneratedArtifactSerializer
    filterset_fields = ("task_execution", "artifact_type", "is_approved")
    search_fields = ("title", "content_text")
    ordering_fields = ("created_at", "updated_at", "approved_at")


class AutomationRuleViewSet(AIBaseViewSet):
    queryset = AutomationRule.objects.select_related("task_type", "prompt_template").all()
    serializer_class = AutomationRuleSerializer
    filterset_fields = ("source_module", "task_type", "priority", "is_active")
    search_fields = ("name", "slug", "trigger_event")
    ordering_fields = ("created_at", "updated_at")

    @action(detail=True, methods=["post"], url_path="run")
    def run(self, request, pk=None):
        rule = self.get_object()
        execution, task_request, artifact = AutomationService.run_automation(
            rule,
            source_reference_type=request.data.get("source_reference_type", ""),
            source_reference_id=request.data.get("source_reference_id", ""),
            integration_event_id=request.data.get("integration_event_id", ""),
            requested_by=request.user,
            input_payload=request.data.get("input_payload", {}),
        )
        return Response(
            {
                "automation_execution": AutomationExecutionSerializer(execution).data,
                "task_request": AITaskRequestSerializer(task_request).data,
                "artifact": AIGeneratedArtifactSerializer(artifact).data,
            },
            status=status.HTTP_200_OK,
        )


class AutomationExecutionViewSet(AIBaseViewSet):
    queryset = AutomationExecution.objects.select_related("automation_rule").all()
    serializer_class = AutomationExecutionSerializer
    filterset_fields = ("automation_rule", "status")
    search_fields = ("source_reference_type", "source_reference_id", "integration_event_id", "output_summary")
    ordering_fields = ("started_at", "completed_at", "updated_at")


class AIAnnotationViewSet(AIBaseViewSet):
    queryset = AIAnnotation.objects.select_related("generated_artifact", "annotated_by").all()
    serializer_class = AIAnnotationSerializer
    filterset_fields = ("generated_artifact", "annotation_type", "annotated_by", "feedback_label")
    search_fields = ("notes", "feedback_label")
    ordering_fields = ("created_at", "updated_at")

    def perform_create(self, serializer):
        serializer.save(annotated_by=self.request.user)


class RetrievalSourceConfigViewSet(AIBaseViewSet):
    queryset = RetrievalSourceConfig.objects.all()
    serializer_class = RetrievalSourceConfigSerializer
    filterset_fields = ("source_type", "source_module", "is_active")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("created_at", "updated_at")


class AIRunTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = RunTaskSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task_request = AITaskRequest.objects.create(
            requested_by=request.user,
            status=AITaskRequest.Status.QUEUED,
            **serializer.validated_data,
        )
        task_request, execution, artifact = AITaskService.run_task(task_request)
        return Response(
            {
                "task_request": AITaskRequestSerializer(task_request).data,
                "execution": AITaskExecutionSerializer(execution).data,
                "artifact": AIGeneratedArtifactSerializer(artifact).data,
            },
            status=status.HTTP_201_CREATED,
        )


class AITaskHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        queryset = AITaskRequest.objects.select_related("task_type", "requested_by").order_by("-created_at")[:50]
        return Response(AITaskRequestSerializer(queryset, many=True).data, status=status.HTTP_200_OK)


class AIAutomationHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        queryset = AutomationExecution.objects.select_related("automation_rule").order_by("-created_at")[:50]
        return Response(AutomationExecutionSerializer(queryset, many=True).data, status=status.HTTP_200_OK)


class AIPromptPreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = PromptPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prompt = serializer.validated_data["prompt_template"]
        preview = PromptTemplateService.render_preview(prompt, serializer.validated_data.get("input_payload", {}))
        return Response({"preview": preview}, status=status.HTTP_200_OK)

