from django.contrib import admin

from .models import (
    ConfiguratorOption,
    ConfiguratorQuestion,
    DeliveryRecord,
    Niche,
    ProductionTask,
    SiteOrder,
    SiteOrderAnswer,
    SiteProjectIntake,
    Template,
    TemplateRecommendationRule,
)


class ConfiguratorOptionInline(admin.TabularInline):
    model = ConfiguratorOption
    extra = 0


@admin.register(Niche)
class NicheAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "niche", "version", "template_type", "status", "base_price", "is_active")
    list_filter = ("niche", "template_type", "status", "is_active")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(ConfiguratorQuestion)
class ConfiguratorQuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "niche", "question_type", "order", "is_active")
    list_filter = ("niche", "question_type", "is_active")
    search_fields = ("text",)
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = (ConfiguratorOptionInline,)


@admin.register(ConfiguratorOption)
class ConfiguratorOptionAdmin(admin.ModelAdmin):
    list_display = ("label", "question", "value", "order", "is_active")
    list_filter = ("is_active", "question")
    search_fields = ("label", "value", "question__text")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(TemplateRecommendationRule)
class TemplateRecommendationRuleAdmin(admin.ModelAdmin):
    list_display = ("niche", "question", "option", "recommended_template", "priority", "is_active")
    list_filter = ("niche", "is_active")
    search_fields = ("niche__name", "recommended_template__name", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")


class SiteOrderAnswerInline(admin.TabularInline):
    model = SiteOrderAnswer
    extra = 0


class ProductionTaskInline(admin.TabularInline):
    model = ProductionTask
    extra = 0
    autocomplete_fields = ("assignee",)


@admin.register(SiteOrder)
class SiteOrderAdmin(admin.ModelAdmin):
    list_display = ("public_id", "company", "requester", "niche", "selected_template", "status", "final_price", "ordered_at")
    list_filter = ("status", "niche", "selected_template")
    search_fields = ("public_id", "company__name", "requester__email", "niche__name")
    readonly_fields = ("public_id", "ordered_at", "production_started_at", "delivered_at", "created_at", "updated_at")
    autocomplete_fields = ("company", "requester", "selected_template", "recommended_template")
    inlines = (SiteOrderAnswerInline, ProductionTaskInline)


@admin.register(SiteProjectIntake)
class SiteProjectIntakeAdmin(admin.ModelAdmin):
    list_display = ("site_order", "company_name", "city", "state", "updated_at")
    search_fields = ("company_name", "site_order__public_id")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(ProductionTask)
class ProductionTaskAdmin(admin.ModelAdmin):
    list_display = ("site_order", "stage", "status", "assignee", "due_date", "order")
    list_filter = ("stage", "status")
    search_fields = ("site_order__public_id", "assignee__email", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("site_order", "assignee")


@admin.register(DeliveryRecord)
class DeliveryRecordAdmin(admin.ModelAdmin):
    list_display = ("site_order", "delivered_url", "delivered_at", "acceptance_status")
    list_filter = ("acceptance_status",)
    search_fields = ("site_order__public_id", "delivered_url")
    readonly_fields = ("public_id", "created_at", "updated_at")
