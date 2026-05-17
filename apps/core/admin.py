from django.contrib import admin

from .models import SystemModule


@admin.register(SystemModule)
class SystemModuleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
