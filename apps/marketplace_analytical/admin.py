from django.contrib import admin

from .models import (
    AnalyticalAssignment,
    AnalyticalMatchingRecord,
    AnalyticalProvider,
    AnalyticalReport,
    AnalyticalRequest,
    AnalyticalReview,
    AnalyticalService,
    AnalyticalServiceCapability,
    AnalyticalServiceCategory,
    AnalyticalServiceRegion,
)


class AnalyticalServiceCapabilityInline(admin.TabularInline):
    model = AnalyticalServiceCapability
    extra = 0


class AnalyticalServiceRegionInline(admin.TabularInline):
    model = AnalyticalServiceRegion
    extra = 0


@admin.register(AnalyticalProvider)
class AnalyticalProviderAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "provider_type",
        "verification_status",
        "marketplace_status",
        "rating_average",
        "completed_jobs_count",
        "is_active",
    )
    list_filter = ("provider_type", "verification_status", "marketplace_status", "is_active")
    search_fields = ("display_name", "legal_name", "document_number", "contact_email", "trust_case_reference")
    readonly_fields = ("public_id", "rating_average", "completed_jobs_count", "created_at", "updated_at")
    autocomplete_fields = ("company", "user")


@admin.register(AnalyticalServiceCategory)
class AnalyticalServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(AnalyticalService)
class AnalyticalServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "provider", "category", "service_type", "delivery_type", "price_model", "is_active")
    list_filter = ("service_type", "delivery_type", "price_model", "is_active")
    search_fields = ("title", "description", "provider__display_name", "category__name")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("provider", "category")
    inlines = (AnalyticalServiceCapabilityInline, AnalyticalServiceRegionInline)


@admin.register(AnalyticalServiceCapability)
class AnalyticalServiceCapabilityAdmin(admin.ModelAdmin):
    list_display = ("analytical_service", "capability_name", "updated_at")
    search_fields = ("analytical_service__title", "capability_name", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("analytical_service",)


@admin.register(AnalyticalServiceRegion)
class AnalyticalServiceRegionAdmin(admin.ModelAdmin):
    list_display = ("analytical_service", "region_name", "state", "country", "coverage_type")
    list_filter = ("country", "state", "coverage_type")
    search_fields = ("analytical_service__title", "region_name", "state", "country")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("analytical_service",)


@admin.register(AnalyticalRequest)
class AnalyticalRequestAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "priority", "status", "origin", "city", "state", "requested_date")
    list_filter = ("category", "priority", "status", "origin", "state")
    search_fields = ("title", "description", "city", "state")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("requester_user", "requester_company", "category", "related_asset", "related_site", "related_service_order")


@admin.register(AnalyticalMatchingRecord)
class AnalyticalMatchingRecordAdmin(admin.ModelAdmin):
    list_display = ("analytical_request", "provider", "match_score", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("analytical_request__title", "provider__display_name", "match_reason")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("analytical_request", "provider")


@admin.register(AnalyticalAssignment)
class AnalyticalAssignmentAdmin(admin.ModelAdmin):
    list_display = ("analytical_request", "provider", "status", "assigned_at", "accepted_at", "completed_at")
    list_filter = ("status",)
    search_fields = ("analytical_request__title", "provider__display_name", "notes")
    readonly_fields = ("public_id", "assigned_at", "accepted_at", "declined_at", "started_at", "completed_at", "created_at", "updated_at")
    autocomplete_fields = ("analytical_request", "provider")


@admin.register(AnalyticalReport)
class AnalyticalReportAdmin(admin.ModelAdmin):
    list_display = ("analytical_assignment", "title", "created_at")
    search_fields = ("title", "summary", "technical_conclusion", "recommendations")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("analytical_assignment",)


@admin.register(AnalyticalReview)
class AnalyticalReviewAdmin(admin.ModelAdmin):
    list_display = ("analytical_assignment", "rating", "reviewer_user", "reviewer_company", "created_at")
    list_filter = ("rating",)
    search_fields = ("comment", "analytical_assignment__analytical_request__title")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("analytical_assignment", "reviewer_user", "reviewer_company")
