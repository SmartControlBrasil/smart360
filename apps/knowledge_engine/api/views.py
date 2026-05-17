from rest_framework import permissions, status, viewsets
from rest_framework.response import Response

from ..models import (
    CauseReference,
    EquipmentReference,
    EquipmentSymptomMap,
    FailureActionMap,
    FailureCauseMap,
    FailureReference,
    KnowledgeCategory,
    KnowledgeFeedback,
    KnowledgeLinkRule,
    KnowledgeTag,
    RecommendedAction,
    SymptomFailureMap,
    SymptomReference,
    TechnicalDocument,
    TroubleshootingArticle,
)
from .serializers import (
    CauseReferenceSerializer,
    EquipmentReferenceSerializer,
    EquipmentSymptomMapSerializer,
    FailureActionMapSerializer,
    FailureCauseMapSerializer,
    FailureReferenceSerializer,
    KnowledgeCategorySerializer,
    KnowledgeFeedbackSerializer,
    KnowledgeLinkRuleSerializer,
    KnowledgeTagSerializer,
    RecommendedActionSerializer,
    SymptomFailureMapSerializer,
    SymptomReferenceSerializer,
    TechnicalDocumentSerializer,
    TroubleshootingArticleSerializer,
)


class KnowledgeBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]


class KnowledgeCategoryViewSet(KnowledgeBaseViewSet):
    queryset = KnowledgeCategory.objects.select_related("parent").all()
    serializer_class = KnowledgeCategorySerializer
    filterset_fields = ("is_active", "parent")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("ordering", "name", "updated_at")


class EquipmentReferenceViewSet(KnowledgeBaseViewSet):
    queryset = EquipmentReference.objects.all()
    serializer_class = EquipmentReferenceSerializer
    filterset_fields = ("manufacturer", "equipment_type", "is_active")
    search_fields = ("name", "slug", "manufacturer", "model", "equipment_type")
    ordering_fields = ("name", "manufacturer", "updated_at")


class SymptomReferenceViewSet(KnowledgeBaseViewSet):
    queryset = SymptomReference.objects.all()
    serializer_class = SymptomReferenceSerializer
    filterset_fields = ("severity_level", "is_active")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "updated_at")


class FailureReferenceViewSet(KnowledgeBaseViewSet):
    queryset = FailureReference.objects.all()
    serializer_class = FailureReferenceSerializer
    filterset_fields = ("criticality", "is_active")
    search_fields = ("name", "slug", "failure_code", "description")
    ordering_fields = ("name", "updated_at")


class CauseReferenceViewSet(KnowledgeBaseViewSet):
    queryset = CauseReference.objects.all()
    serializer_class = CauseReferenceSerializer
    filterset_fields = ("cause_type", "is_active")
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "updated_at")


class RecommendedActionViewSet(KnowledgeBaseViewSet):
    queryset = RecommendedAction.objects.all()
    serializer_class = RecommendedActionSerializer
    filterset_fields = ("action_type", "priority", "is_active")
    search_fields = ("title", "slug", "description")
    ordering_fields = ("title", "updated_at")


class TroubleshootingArticleViewSet(KnowledgeBaseViewSet):
    queryset = TroubleshootingArticle.objects.select_related("category", "created_by", "reviewed_by").all()
    serializer_class = TroubleshootingArticleSerializer
    filterset_fields = ("category", "status", "is_active")
    search_fields = ("title", "slug", "summary", "content")
    ordering_fields = ("published_at", "created_at", "updated_at")


class TechnicalDocumentViewSet(KnowledgeBaseViewSet):
    queryset = TechnicalDocument.objects.select_related("category", "equipment_reference", "created_by").all()
    serializer_class = TechnicalDocumentSerializer
    filterset_fields = ("document_type", "category", "equipment_reference", "status", "is_active")
    search_fields = ("title", "slug", "manufacturer", "version", "summary")
    ordering_fields = ("title", "created_at", "updated_at")


class KnowledgeTagViewSet(KnowledgeBaseViewSet):
    queryset = KnowledgeTag.objects.all()
    serializer_class = KnowledgeTagSerializer
    search_fields = ("name", "slug", "description")
    ordering_fields = ("name", "updated_at")


class KnowledgeLinkRuleViewSet(KnowledgeBaseViewSet):
    queryset = KnowledgeLinkRule.objects.all()
    serializer_class = KnowledgeLinkRuleSerializer
    filterset_fields = ("source_type", "target_type", "relation_type")
    search_fields = ("notes",)
    ordering_fields = ("created_at", "updated_at")


class EquipmentSymptomMapViewSet(KnowledgeBaseViewSet):
    queryset = EquipmentSymptomMap.objects.select_related("equipment_reference", "symptom_reference").all()
    serializer_class = EquipmentSymptomMapSerializer
    filterset_fields = ("equipment_reference", "symptom_reference")
    search_fields = ("equipment_reference__name", "symptom_reference__name", "notes")
    ordering_fields = ("created_at", "updated_at")


class SymptomFailureMapViewSet(KnowledgeBaseViewSet):
    queryset = SymptomFailureMap.objects.select_related("symptom_reference", "failure_reference").all()
    serializer_class = SymptomFailureMapSerializer
    filterset_fields = ("symptom_reference", "failure_reference")
    search_fields = ("symptom_reference__name", "failure_reference__name", "notes")
    ordering_fields = ("created_at", "updated_at")


class FailureCauseMapViewSet(KnowledgeBaseViewSet):
    queryset = FailureCauseMap.objects.select_related("failure_reference", "cause_reference").all()
    serializer_class = FailureCauseMapSerializer
    filterset_fields = ("failure_reference", "cause_reference")
    search_fields = ("failure_reference__name", "cause_reference__name", "notes")
    ordering_fields = ("created_at", "updated_at")


class FailureActionMapViewSet(KnowledgeBaseViewSet):
    queryset = FailureActionMap.objects.select_related("failure_reference", "recommended_action").all()
    serializer_class = FailureActionMapSerializer
    filterset_fields = ("failure_reference", "recommended_action")
    search_fields = ("failure_reference__name", "recommended_action__title", "notes")
    ordering_fields = ("priority", "created_at", "updated_at")


class KnowledgeFeedbackViewSet(KnowledgeBaseViewSet):
    queryset = KnowledgeFeedback.objects.select_related("user").all()
    serializer_class = KnowledgeFeedbackSerializer
    filterset_fields = ("item_type", "usefulness_rating", "user")
    search_fields = ("comment", "user__email")
    ordering_fields = ("created_at", "updated_at")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        feedback = serializer.save()
        output = KnowledgeFeedbackSerializer(feedback, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)
