from django.contrib import admin

from .models import (
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


@admin.register(KnowledgeCategory)
class KnowledgeCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "ordering", "is_active", "updated_at")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("parent",)


@admin.register(EquipmentReference)
class EquipmentReferenceAdmin(admin.ModelAdmin):
    list_display = ("name", "manufacturer", "model", "equipment_type", "is_active")
    list_filter = ("is_active", "manufacturer", "equipment_type")
    search_fields = ("name", "slug", "manufacturer", "model", "equipment_type")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(SymptomReference)
class SymptomReferenceAdmin(admin.ModelAdmin):
    list_display = ("name", "severity_level", "is_active", "updated_at")
    list_filter = ("severity_level", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(FailureReference)
class FailureReferenceAdmin(admin.ModelAdmin):
    list_display = ("name", "failure_code", "criticality", "is_active", "updated_at")
    list_filter = ("criticality", "is_active")
    search_fields = ("name", "slug", "failure_code", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(CauseReference)
class CauseReferenceAdmin(admin.ModelAdmin):
    list_display = ("name", "cause_type", "is_active", "updated_at")
    list_filter = ("cause_type", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(RecommendedAction)
class RecommendedActionAdmin(admin.ModelAdmin):
    list_display = ("title", "action_type", "priority", "is_active", "updated_at")
    list_filter = ("action_type", "priority", "is_active")
    search_fields = ("title", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(TroubleshootingArticle)
class TroubleshootingArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "is_active", "published_at")
    list_filter = ("status", "is_active", "category")
    search_fields = ("title", "slug", "summary", "content")
    readonly_fields = ("public_id", "published_at", "created_at", "updated_at")
    autocomplete_fields = ("category", "created_by", "reviewed_by")


@admin.register(TechnicalDocument)
class TechnicalDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "document_type", "category", "manufacturer", "status", "is_active")
    list_filter = ("document_type", "status", "is_active", "category")
    search_fields = ("title", "slug", "manufacturer", "version", "summary")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("category", "equipment_reference", "created_by")


@admin.register(KnowledgeTag)
class KnowledgeTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "updated_at")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(KnowledgeLinkRule)
class KnowledgeLinkRuleAdmin(admin.ModelAdmin):
    list_display = ("source_type", "source_id", "relation_type", "target_type", "target_id", "updated_at")
    list_filter = ("source_type", "target_type", "relation_type")
    search_fields = ("notes",)
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(EquipmentSymptomMap)
class EquipmentSymptomMapAdmin(admin.ModelAdmin):
    list_display = ("equipment_reference", "symptom_reference", "confidence_level", "updated_at")
    search_fields = ("equipment_reference__name", "symptom_reference__name", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("equipment_reference", "symptom_reference")


@admin.register(SymptomFailureMap)
class SymptomFailureMapAdmin(admin.ModelAdmin):
    list_display = ("symptom_reference", "failure_reference", "confidence_level", "updated_at")
    search_fields = ("symptom_reference__name", "failure_reference__name", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("symptom_reference", "failure_reference")


@admin.register(FailureCauseMap)
class FailureCauseMapAdmin(admin.ModelAdmin):
    list_display = ("failure_reference", "cause_reference", "confidence_level", "updated_at")
    search_fields = ("failure_reference__name", "cause_reference__name", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("failure_reference", "cause_reference")


@admin.register(FailureActionMap)
class FailureActionMapAdmin(admin.ModelAdmin):
    list_display = ("failure_reference", "recommended_action", "priority", "updated_at")
    search_fields = ("failure_reference__name", "recommended_action__title", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("failure_reference", "recommended_action")


@admin.register(KnowledgeFeedback)
class KnowledgeFeedbackAdmin(admin.ModelAdmin):
    list_display = ("item_type", "item_id", "usefulness_rating", "user", "created_at")
    list_filter = ("item_type", "usefulness_rating")
    search_fields = ("comment", "user__email")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("user",)
