from rest_framework import serializers

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
from ..services.knowledge_service import KnowledgeFeedbackService


class KnowledgeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeCategory
        fields = ("public_id", "name", "slug", "description", "is_active", "ordering", "parent", "created_at", "updated_at")
        read_only_fields = ("public_id", "slug", "created_at", "updated_at")


class EquipmentReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentReference
        fields = (
            "public_id",
            "name",
            "slug",
            "manufacturer",
            "model",
            "equipment_type",
            "description",
            "is_active",
            "notes",
            "metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "slug", "created_at", "updated_at")


class SymptomReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SymptomReference
        fields = ("public_id", "name", "slug", "description", "severity_level", "is_active", "created_at", "updated_at")
        read_only_fields = ("public_id", "slug", "created_at", "updated_at")


class FailureReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FailureReference
        fields = ("public_id", "name", "slug", "description", "failure_code", "criticality", "is_active", "notes", "created_at", "updated_at")
        read_only_fields = ("public_id", "slug", "created_at", "updated_at")


class CauseReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CauseReference
        fields = ("public_id", "name", "slug", "description", "cause_type", "is_active", "notes", "created_at", "updated_at")
        read_only_fields = ("public_id", "slug", "created_at", "updated_at")


class RecommendedActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendedAction
        fields = ("public_id", "title", "slug", "description", "action_type", "priority", "is_active", "notes", "created_at", "updated_at")
        read_only_fields = ("public_id", "slug", "created_at", "updated_at")


class TroubleshootingArticleSerializer(serializers.ModelSerializer):
    class Meta:
        model = TroubleshootingArticle
        fields = (
            "public_id",
            "title",
            "slug",
            "category",
            "summary",
            "content",
            "status",
            "created_by",
            "reviewed_by",
            "published_at",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "slug", "published_at", "created_at", "updated_at")


class TechnicalDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnicalDocument
        fields = (
            "public_id",
            "title",
            "slug",
            "document_type",
            "category",
            "equipment_reference",
            "manufacturer",
            "version",
            "file",
            "external_url",
            "summary",
            "status",
            "is_active",
            "created_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("public_id", "slug", "created_at", "updated_at")


class KnowledgeTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeTag
        fields = ("public_id", "name", "slug", "description", "created_at", "updated_at")
        read_only_fields = ("public_id", "slug", "created_at", "updated_at")


class KnowledgeLinkRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeLinkRule
        fields = ("public_id", "source_type", "source_id", "target_type", "target_id", "relation_type", "notes", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class EquipmentSymptomMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentSymptomMap
        fields = ("public_id", "equipment_reference", "symptom_reference", "notes", "confidence_level", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class SymptomFailureMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = SymptomFailureMap
        fields = ("public_id", "symptom_reference", "failure_reference", "notes", "confidence_level", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class FailureCauseMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = FailureCauseMap
        fields = ("public_id", "failure_reference", "cause_reference", "notes", "confidence_level", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class FailureActionMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = FailureActionMap
        fields = ("public_id", "failure_reference", "recommended_action", "notes", "priority", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")


class KnowledgeFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeFeedback
        fields = ("public_id", "user", "item_type", "item_id", "usefulness_rating", "comment", "created_at", "updated_at")
        read_only_fields = ("public_id", "created_at", "updated_at")

    def create(self, validated_data):
        return KnowledgeFeedbackService.create_feedback(user=self.context["request"].user, validated_data=validated_data)
