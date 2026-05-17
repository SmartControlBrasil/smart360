from django.contrib import admin

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


class PromptVersionInline(admin.TabularInline):
    model = PromptVersion
    extra = 0


@admin.register(AITaskType)
class AITaskTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "task_category", "is_active", "created_at")
    list_filter = ("task_category", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "task_type", "source_module", "version_label", "model_hint", "is_active")
    list_filter = ("task_type", "source_module", "is_active")
    search_fields = ("name", "slug", "prompt_template")
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = [PromptVersionInline]


@admin.register(PromptVersion)
class PromptVersionAdmin(admin.ModelAdmin):
    list_display = ("prompt_template", "version_label", "created_by", "created_at")
    list_filter = ("prompt_template",)
    search_fields = ("prompt_template__name", "version_label", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(AIContextProfile)
class AIContextProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "source_module", "is_active", "updated_at")
    list_filter = ("source_module", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(AIModelConfig)
class AIModelConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "provider_name", "model_identifier", "model_type", "is_active")
    list_filter = ("provider_name", "model_type", "is_active")
    search_fields = ("name", "slug", "model_identifier")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(AITaskRequest)
class AITaskRequestAdmin(admin.ModelAdmin):
    list_display = ("task_type", "source_module", "status", "priority", "requested_by", "created_at")
    list_filter = ("task_type", "source_module", "status", "priority")
    search_fields = ("source_reference_type", "source_reference_id", "error_message")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(AITaskExecution)
class AITaskExecutionAdmin(admin.ModelAdmin):
    list_display = ("task_request", "execution_mode", "provider_name", "model_name", "status", "started_at")
    list_filter = ("execution_mode", "provider_name", "status")
    search_fields = ("task_request__source_reference_id", "output_text", "error_message")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(AIGeneratedArtifact)
class AIGeneratedArtifactAdmin(admin.ModelAdmin):
    list_display = ("artifact_type", "task_execution", "is_approved", "approved_by", "created_at")
    list_filter = ("artifact_type", "is_approved")
    search_fields = ("title", "content_text")
    readonly_fields = ("public_id", "created_at", "updated_at", "approved_at")


@admin.register(AutomationRule)
class AutomationRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "source_module", "trigger_event", "task_type", "priority", "is_active")
    list_filter = ("source_module", "task_type", "priority", "is_active")
    search_fields = ("name", "slug", "trigger_event")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(AutomationExecution)
class AutomationExecutionAdmin(admin.ModelAdmin):
    list_display = ("automation_rule", "source_reference_type", "integration_event_id", "status", "started_at")
    list_filter = ("status", "automation_rule__source_module")
    search_fields = ("source_reference_type", "source_reference_id", "integration_event_id", "output_summary")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(AIAnnotation)
class AIAnnotationAdmin(admin.ModelAdmin):
    list_display = ("generated_artifact", "annotation_type", "feedback_label", "annotated_by", "created_at")
    list_filter = ("annotation_type", "feedback_label")
    search_fields = ("notes",)
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(RetrievalSourceConfig)
class RetrievalSourceConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "source_type", "source_module", "is_active", "created_at")
    list_filter = ("source_type", "source_module", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")

