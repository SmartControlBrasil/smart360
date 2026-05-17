from django.contrib import admin

from .models import IntegrationCredential


@admin.register(IntegrationCredential)
class IntegrationCredentialAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "company", "key_prefix", "is_active", "last_used_at", "expires_at")
    list_filter = ("is_active", "company")
    search_fields = ("name", "user__email", "company__name", "key_prefix")
    readonly_fields = ("public_id", "key_prefix", "last_used_at", "created_at", "updated_at")
    autocomplete_fields = ("user", "company", "created_by")

