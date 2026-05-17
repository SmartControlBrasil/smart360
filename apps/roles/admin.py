from django.contrib import admin

from .models import Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("label", "code", "scope", "is_system", "is_active")
    list_filter = ("scope", "is_system", "is_active")
    search_fields = ("label", "code", "description")
    readonly_fields = ("public_id", "created_at", "updated_at")
