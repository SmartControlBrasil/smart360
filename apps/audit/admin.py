from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "entity", "entity_id", "user", "company", "created_at")
    list_filter = ("action", "entity", "created_at")
    search_fields = ("entity", "entity_id", "user__email", "company__name")
    readonly_fields = ("public_id", "created_at")
