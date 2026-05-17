from django.contrib import admin

from .models import Company, Membership, SiteMembership


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    autocomplete_fields = ("user", "roles")


class SiteMembershipInline(admin.TabularInline):
    model = SiteMembership
    extra = 0
    autocomplete_fields = ("user", "company", "site")


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "status", "email", "phone_number", "updated_at")
    list_filter = ("status",)
    search_fields = ("name", "legal_name", "slug", "tax_id", "email")
    readonly_fields = ("public_id", "created_at", "updated_at")
    inlines = (MembershipInline, SiteMembershipInline)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "status", "is_primary", "joined_at")
    list_filter = ("status", "is_primary", "roles")
    search_fields = ("user__email", "company__name", "company__slug")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("user", "company", "roles")


@admin.register(SiteMembership)
class SiteMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "site", "status", "is_primary", "updated_at")
    list_filter = ("status", "is_primary", "company")
    search_fields = ("user__email", "company__name", "site__name", "site__code")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("user", "company", "site")
