from django.contrib import admin

from .models import SearchBoostRule, SearchIndexEntry, SearchQueryLog, SearchSavedFilter, SearchSynonym


@admin.register(SearchIndexEntry)
class SearchIndexEntryAdmin(admin.ModelAdmin):
    list_display = ("title", "source_module", "item_type", "item_id", "status", "category", "is_active", "updated_at")
    list_filter = ("source_module", "item_type", "status", "category", "is_active")
    search_fields = ("title", "subtitle", "body_text", "search_text", "item_id", "url_path")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(SearchQueryLog)
class SearchQueryLogAdmin(admin.ModelAdmin):
    list_display = ("query_text", "performed_by", "source_context", "results_count", "executed_at")
    list_filter = ("source_context", "executed_at")
    search_fields = ("query_text", "performed_by__email")
    readonly_fields = ("public_id", "executed_at", "created_at")
    autocomplete_fields = ("performed_by",)


@admin.register(SearchSavedFilter)
class SearchSavedFilterAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner_user", "owner_company", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    readonly_fields = ("public_id", "created_at", "updated_at")
    autocomplete_fields = ("owner_user", "owner_company")


@admin.register(SearchSynonym)
class SearchSynonymAdmin(admin.ModelAdmin):
    list_display = ("term", "synonym", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("term", "synonym")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(SearchBoostRule)
class SearchBoostRuleAdmin(admin.ModelAdmin):
    list_display = ("source_module", "item_type", "status", "boost_value", "is_active", "updated_at")
    list_filter = ("source_module", "item_type", "status", "is_active")
    search_fields = ("source_module", "item_type", "status")
    readonly_fields = ("public_id", "created_at", "updated_at")

