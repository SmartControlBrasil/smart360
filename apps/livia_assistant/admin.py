from django.contrib import admin

from .models import LiviaConversation, LiviaHandoffRequest, LiviaKnowledgeItem, LiviaLeadCapture, LiviaMessage


class LiviaMessageInline(admin.TabularInline):
    model = LiviaMessage
    extra = 0
    fields = ("role", "content", "created_at")
    readonly_fields = ("created_at",)


class LiviaLeadCaptureInline(admin.TabularInline):
    model = LiviaLeadCapture
    extra = 0
    fields = ("name", "phone", "email", "service_interest", "urgency", "is_qualified", "created_at")
    readonly_fields = ("created_at",)


@admin.register(LiviaConversation)
class LiviaConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "session_key", "visitor_name", "visitor_phone", "status", "source_page", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("session_key", "visitor_name", "visitor_email", "visitor_phone", "company_name", "messages__content")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")
    inlines = (LiviaMessageInline, LiviaLeadCaptureInline)


@admin.register(LiviaMessage)
class LiviaMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("content", "conversation__session_key")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(LiviaLeadCapture)
class LiviaLeadCaptureAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "company", "phone", "service_interest", "urgency", "is_qualified", "operational_status", "crm_lead_id", "created_at")
    list_filter = ("urgency", "is_qualified", "operational_status", "created_at")
    search_fields = ("name", "email", "phone", "company", "city", "service_interest", "notes")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(LiviaHandoffRequest)
class LiviaHandoffRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "status", "created_at", "resolved_at")
    list_filter = ("status", "created_at", "resolved_at")
    search_fields = ("reason", "conversation__session_key", "conversation__visitor_name", "conversation__visitor_phone", "conversation__visitor_email", "conversation__company_name")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)


@admin.register(LiviaKnowledgeItem)
class LiviaKnowledgeItemAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_active", "priority", "updated_at")
    list_filter = ("category", "is_active")
    search_fields = ("title", "content", "keywords")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-priority", "title")
