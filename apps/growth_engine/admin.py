from django.contrib import admin

from .models import CommercialProposal, Lead, LeadAssignment, LeadCampaign, LeadInteraction, LeadQualification, LeadSource, LeadTag


class LeadInteractionInline(admin.TabularInline):
    model = LeadInteraction
    extra = 0
    autocomplete_fields = ("owner",)


class LeadAssignmentInline(admin.TabularInline):
    model = LeadAssignment
    extra = 0
    autocomplete_fields = ("user",)


@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "source_type", "is_active", "updated_at")
    list_filter = ("source_type", "is_active")
    search_fields = ("name", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(LeadTag)
class LeadTagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "updated_at")
    search_fields = ("name", "slug")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(LeadCampaign)
class LeadCampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "channel", "status", "objective", "updated_at")
    list_filter = ("channel", "status")
    search_fields = ("name", "objective", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("company_name", "contact_name", "status", "score", "city", "state", "source", "assigned_to")
    list_filter = ("status", "state", "source", "niche", "tags")
    search_fields = ("company_name", "contact_name", "email", "phone", "whatsapp", "website")
    readonly_fields = ("public_id", "score", "created_at", "updated_at")
    autocomplete_fields = ("source", "campaign", "niche", "assigned_to", "created_by", "tags")
    inlines = (LeadInteractionInline, LeadAssignmentInline)


@admin.register(LeadInteraction)
class LeadInteractionAdmin(admin.ModelAdmin):
    list_display = ("lead", "interaction_type", "channel", "owner", "happened_at")
    list_filter = ("interaction_type", "channel")
    search_fields = ("lead__company_name", "summary", "owner__email")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("lead", "owner")


@admin.register(LeadQualification)
class LeadQualificationAdmin(admin.ModelAdmin):
    list_display = ("lead", "calculated_score", "updated_at")
    search_fields = ("lead__company_name", "notes")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("lead",)


@admin.register(LeadAssignment)
class LeadAssignmentAdmin(admin.ModelAdmin):
    list_display = ("lead", "user", "status", "assigned_at")
    list_filter = ("status",)
    search_fields = ("lead__company_name", "user__email")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("lead", "user")


@admin.register(CommercialProposal)
class CommercialProposalAdmin(admin.ModelAdmin):
    list_display = ("proposal_number", "lead", "company_name", "status", "origin", "total_value", "created_at")
    list_filter = ("status", "origin", "created_at")
    search_fields = ("proposal_number", "company_name", "contact_name", "email", "phone", "service_interest", "summary")
    readonly_fields = ("public_id", "proposal_number", "created_at", "updated_at")
    autocomplete_fields = ("lead", "created_by", "updated_by")
