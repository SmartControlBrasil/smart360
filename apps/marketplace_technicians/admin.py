from django.contrib import admin

from .models import (
    ServiceRegion,
    TechnicianAssignment,
    TechnicianAvailability,
    TechnicianCompensationRecord,
    TechnicianMatchingRecord,
    TechnicianPortfolioItem,
    TechnicianProfile,
    TechnicianReview,
    TechnicianServiceOffer,
    TechnicianServiceRegion,
    TechnicianServiceRequest,
    TechnicianSkill,
    TechnicianSkillAssignment,
    TechnicianWorkReport,
)


class TechnicianSkillAssignmentInline(admin.TabularInline):
    model = TechnicianSkillAssignment
    extra = 0


class TechnicianServiceRegionInline(admin.TabularInline):
    model = TechnicianServiceRegion
    extra = 0


class TechnicianAvailabilityInline(admin.TabularInline):
    model = TechnicianAvailability
    extra = 0


class TechnicianPortfolioItemInline(admin.TabularInline):
    model = TechnicianPortfolioItem
    extra = 0


@admin.register(TechnicianProfile)
class TechnicianProfileAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "user",
        "company",
        "profile_type",
        "verification_status",
        "marketplace_status",
        "rating_average",
        "completed_jobs_count",
        "is_active",
    )
    list_filter = ("profile_type", "verification_status", "marketplace_status", "is_active")
    search_fields = ("display_name", "user__email", "company__name", "document_number", "phone", "whatsapp", "trust_case_reference")
    readonly_fields = ("public_id", "rating_average", "completed_jobs_count", "created_at", "updated_at")
    autocomplete_fields = ("user", "company")
    inlines = (
        TechnicianSkillAssignmentInline,
        TechnicianServiceRegionInline,
        TechnicianAvailabilityInline,
        TechnicianPortfolioItemInline,
    )


@admin.register(TechnicianSkill)
class TechnicianSkillAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(TechnicianSkillAssignment)
class TechnicianSkillAssignmentAdmin(admin.ModelAdmin):
    list_display = ("technician_profile", "skill", "proficiency_level", "years_experience")
    list_filter = ("proficiency_level",)
    search_fields = ("technician_profile__display_name", "skill__name", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("technician_profile", "skill")


@admin.register(ServiceRegion)
class ServiceRegionAdmin(admin.ModelAdmin):
    list_display = ("name", "state", "city", "region_type", "is_active")
    list_filter = ("region_type", "state", "is_active")
    search_fields = ("name", "state", "city")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(TechnicianServiceRegion)
class TechnicianServiceRegionAdmin(admin.ModelAdmin):
    list_display = ("technician_profile", "service_region", "coverage_type")
    list_filter = ("coverage_type",)
    search_fields = ("technician_profile__display_name", "service_region__name", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("technician_profile", "service_region")


@admin.register(TechnicianAvailability)
class TechnicianAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("technician_profile", "weekday", "start_time", "end_time", "is_available")
    list_filter = ("weekday", "is_available")
    search_fields = ("technician_profile__display_name", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("technician_profile",)


@admin.register(TechnicianPortfolioItem)
class TechnicianPortfolioItemAdmin(admin.ModelAdmin):
    list_display = ("technician_profile", "title", "ordering", "is_active")
    list_filter = ("is_active",)
    search_fields = ("technician_profile__display_name", "title", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("technician_profile",)


@admin.register(TechnicianServiceRequest)
class TechnicianServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("title", "requester_company", "category", "service_type", "priority", "status", "origin", "city", "state")
    list_filter = ("service_type", "priority", "status", "origin", "state", "requester_company")
    search_fields = ("title", "description", "category", "city", "state", "address_line", "location_label")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = (
        "requester_user",
        "requester_company",
        "related_client",
        "related_site",
        "related_asset",
        "related_service_order",
    )


@admin.register(TechnicianServiceOffer)
class TechnicianServiceOfferAdmin(admin.ModelAdmin):
    list_display = ("service_request", "technician_profile", "proposed_amount", "estimated_hours", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("service_request__title", "technician_profile__display_name", "message")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("service_request", "technician_profile")


@admin.register(TechnicianMatchingRecord)
class TechnicianMatchingRecordAdmin(admin.ModelAdmin):
    list_display = (
        "technician_service_request",
        "technician_profile",
        "ranking_position",
        "match_score",
        "score_specialty",
        "score_distance",
        "score_rating",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = ("technician_service_request__title", "technician_profile__display_name", "match_reason")
    readonly_fields = (
        "public_id",
        "ranking_position",
        "match_score",
        "score_specialty",
        "score_distance",
        "score_rating",
        "score_experience",
        "score_availability",
        "score_response_time",
        "distance_km",
        "scoring_version",
        "calculation_context",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("technician_service_request", "technician_profile")


@admin.register(TechnicianAssignment)
class TechnicianAssignmentAdmin(admin.ModelAdmin):
    list_display = ("technician_service_request", "technician_profile", "service_offer", "assignment_status", "assigned_at", "accepted_at", "completed_at")
    list_filter = ("assignment_status",)
    search_fields = ("technician_service_request__title", "technician_profile__display_name", "notes")
    readonly_fields = ("public_id", "assigned_at", "accepted_at", "declined_at", "started_at", "completed_at", "created_at", "updated_at")
    autocomplete_fields = ("technician_service_request", "technician_profile", "service_offer")


@admin.register(TechnicianWorkReport)
class TechnicianWorkReportAdmin(admin.ModelAdmin):
    list_display = ("technician_assignment", "summary", "started_at", "ended_at", "labor_minutes")
    search_fields = ("technician_assignment__technician_service_request__title", "summary", "execution_notes")
    readonly_fields = ("public_id", "labor_minutes", "created_at", "updated_at")
    autocomplete_fields = ("technician_assignment",)


@admin.register(TechnicianReview)
class TechnicianReviewAdmin(admin.ModelAdmin):
    list_display = ("technician_profile", "assignment", "rating", "status", "created_at")
    list_filter = ("rating", "status")
    search_fields = ("technician_profile__display_name", "comment")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("technician_profile", "assignment", "reviewer_user", "reviewer_company")


@admin.register(TechnicianCompensationRecord)
class TechnicianCompensationRecordAdmin(admin.ModelAdmin):
    list_display = ("technician_assignment", "gross_amount", "platform_fee", "net_amount", "status")
    list_filter = ("status",)
    search_fields = ("technician_assignment__technician_service_request__title", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("technician_assignment",)
