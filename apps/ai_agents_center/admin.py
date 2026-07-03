from django.contrib import admin, messages

from apps.ai_agents_center.services.opportunity_builder import OpportunityBuilderService
from apps.ai_agents_center.models import (
    AgentActionProposal,
    AgentAnomalyAttentionFlag,
    AgentAssetAttentionFlag,
    AgentDefinition,
    AgentExecutionPolicy,
    AgentMarketplaceRequestFlag,
    AgentMemoryEntry,
    AgentProfitabilityAttentionFlag,
    AgentRecommendation,
    AgentRun,
    AgentScheduleHealthFlag,
    AIBriefing,
    AIBriefingConfiguration,
    AIBriefingDelivery,
    CommercialOpportunity,
    AtlasProspectImportBatch,
    ClientPortalCopilotConfiguration,
    ClientPortalCopilotMessage,
    ClientPortalCopilotSession,
    ManagerCopilotConfiguration,
    ManagerCopilotMessage,
    ManagerCopilotSession,
    TechnicianCopilotConfiguration,
    TechnicianCopilotMessage,
    TechnicianCopilotSession,
    AtlasLead,
    PendingAtlasLead,
)


@admin.register(AgentDefinition)
class AgentDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "domain", "autonomy_level", "status", "enabled", "updated_at")
    list_filter = ("domain", "status", "enabled", "autonomy_level")
    search_fields = ("name", "slug", "description")


@admin.register(AgentExecutionPolicy)
class AgentExecutionPolicyAdmin(admin.ModelAdmin):
    list_display = ("agent", "require_human_approval", "allow_manual_runs", "allow_scheduled_runs", "is_active")
    list_filter = ("require_human_approval", "allow_manual_runs", "allow_scheduled_runs", "is_active")
    search_fields = ("agent__name", "agent__slug")


@admin.register(AgentRun)
class AgentRunAdmin(admin.ModelAdmin):
    list_display = ("agent", "trigger_type", "company", "site", "status", "started_at", "finished_at")
    list_filter = ("agent", "trigger_type", "status", "company")
    search_fields = ("agent__name", "trigger_reference", "request_id", "correlation_id")


@admin.register(AgentRecommendation)
class AgentRecommendationAdmin(admin.ModelAdmin):
    list_display = ("title", "recommendation_type", "severity", "priority", "attention_score", "status", "company", "site", "created_at")
    list_filter = ("recommendation_type", "severity", "priority", "status", "company")
    search_fields = ("title", "summary", "entity_type", "entity_id")


@admin.register(AgentActionProposal)
class AgentActionProposalAdmin(admin.ModelAdmin):
    list_display = ("action_type", "priority", "target_entity", "status", "approval_required", "created_at")
    list_filter = ("status", "approval_required", "action_type", "priority")
    search_fields = ("action_type", "target_entity", "target_entity_id")


@admin.register(AgentAssetAttentionFlag)
class AgentAssetAttentionFlagAdmin(admin.ModelAdmin):
    list_display = ("asset", "company", "site", "risk_level", "attention_score", "status", "updated_at")
    list_filter = ("risk_level", "status", "company", "site")
    search_fields = ("asset__asset_tag", "asset__name", "summary")


@admin.register(AgentScheduleHealthFlag)
class AgentScheduleHealthFlagAdmin(admin.ModelAdmin):
    list_display = ("flag_type", "technician", "company", "site", "schedule_date", "risk_level", "attention_score", "status", "updated_at")
    list_filter = ("flag_type", "risk_level", "status", "company", "site", "schedule_date")
    search_fields = ("technician__email", "technician__first_name", "technician__last_name", "summary")


@admin.register(AgentProfitabilityAttentionFlag)
class AgentProfitabilityAttentionFlagAdmin(admin.ModelAdmin):
    list_display = ("focus_type", "display_label", "company", "site", "risk_level", "attention_score", "status", "updated_at")
    list_filter = ("focus_type", "risk_level", "status", "company", "site")
    search_fields = ("display_label", "summary", "target_entity_type", "target_entity_id")


@admin.register(AgentMarketplaceRequestFlag)
class AgentMarketplaceRequestFlagAdmin(admin.ModelAdmin):
    list_display = ("service_request", "company", "site", "risk_level", "attention_score", "status", "updated_at")
    list_filter = ("risk_level", "status", "company", "site")
    search_fields = ("service_request__title", "summary", "service_request__city", "service_request__state")


@admin.register(AgentAnomalyAttentionFlag)
class AgentAnomalyAttentionFlagAdmin(admin.ModelAdmin):
    list_display = ("focus_type", "display_label", "company", "site", "risk_level", "attention_score", "status", "updated_at")
    list_filter = ("focus_type", "risk_level", "status", "company", "site")
    search_fields = ("display_label", "summary", "target_entity_type", "target_entity_id")


@admin.register(CommercialOpportunity)
class CommercialOpportunityAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company_name",
        "segment",
        "city",
        "state",
        "source",
        "confidence_score",
        "commercial_score",
        "status",
        "outreach_channel",
        "outreach_status",
        "created_at",
    )
    list_filter = ("status", "source", "segment", "city", "state", "outreach_channel", "outreach_status")
    search_fields = (
        "company_name",
        "title",
        "opportunity_description",
        "recommended_product",
        "recommended_solution",
    )
    readonly_fields = (
        "public_id",
        "created_at",
        "updated_at",
        "converted_at",
        "reviewed_at",
        "outreach_channel",
        "outreach_sender_email",
        "outreach_domain",
        "outreach_status",
        "outreach_notes",
    )
    actions = ("approve_selected_opportunities", "reject_selected_opportunities", "convert_approved_opportunities_to_lead")

    @admin.action(description="Approve selected opportunities")
    def approve_selected_opportunities(self, request, queryset):
        approved = 0
        blocked = 0
        for opportunity in queryset:
            try:
                OpportunityBuilderService.approve(opportunity=opportunity, user=request.user)
                approved += 1
            except ValueError:
                blocked += 1
        if approved:
            self.message_user(request, f"{approved} opportunity/opportunities approved.", messages.SUCCESS)
        if blocked:
            self.message_user(request, f"{blocked} opportunity/opportunities could not be approved.", messages.WARNING)

    @admin.action(description="Reject selected opportunities")
    def reject_selected_opportunities(self, request, queryset):
        rejected = 0
        blocked = 0
        for opportunity in queryset:
            try:
                OpportunityBuilderService.reject(opportunity=opportunity, user=request.user, reason="Rejected from admin action.")
                rejected += 1
            except ValueError:
                blocked += 1
        if rejected:
            self.message_user(request, f"{rejected} opportunity/opportunities rejected.", messages.SUCCESS)
        if blocked:
            self.message_user(request, f"{blocked} opportunity/opportunities could not be rejected.", messages.WARNING)

    @admin.action(description="Convert approved opportunities to lead")
    def convert_approved_opportunities_to_lead(self, request, queryset):
        converted = 0
        blocked = 0
        for opportunity in queryset:
            try:
                OpportunityBuilderService.convert_to_lead(opportunity=opportunity, user=request.user)
                converted += 1
            except ValueError:
                blocked += 1
        if converted:
            self.message_user(request, f"{converted} opportunity/opportunities converted to lead.", messages.SUCCESS)
        if blocked:
            self.message_user(request, f"{blocked} opportunity/opportunities were not approved or already converted.", messages.WARNING)


@admin.register(AtlasProspectImportBatch)
class AtlasProspectImportBatchAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "source",
        "filename",
        "status",
        "total_rows",
        "processed_rows",
        "created_opportunities",
        "skipped_duplicates",
        "skipped_empty_rows",
        "company",
        "created_at",
    )
    list_filter = ("status", "source", "company")
    search_fields = ("filename", "public_id")
    readonly_fields = (
        "public_id",
        "company",
        "created_by",
        "source",
        "filename",
        "total_rows",
        "processed_rows",
        "created_opportunities",
        "skipped_duplicates",
        "skipped_empty_rows",
        "errors",
        "status",
        "created_at",
        "updated_at",
    )


@admin.register(AgentMemoryEntry)
class AgentMemoryEntryAdmin(admin.ModelAdmin):
    list_display = ("agent", "memory_kind", "company", "site", "entity_type", "entity_id", "created_at")
    list_filter = ("memory_kind", "company", "site")
    search_fields = ("agent__name", "entity_type", "entity_id", "content")


@admin.register(ManagerCopilotConfiguration)
class ManagerCopilotConfigurationAdmin(admin.ModelAdmin):
    list_display = ("company", "is_enabled", "updated_at")
    list_filter = ("is_enabled",)
    search_fields = ("company__name",)


@admin.register(ManagerCopilotSession)
class ManagerCopilotSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "company", "site", "status", "last_intent", "message_count", "last_activity_at")
    list_filter = ("status", "company", "site", "last_intent")
    search_fields = ("title", "user__email", "last_query")


@admin.register(ManagerCopilotMessage)
class ManagerCopilotMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "role", "detected_intent", "created_at")
    list_filter = ("role", "detected_intent")
    search_fields = ("content", "session__title", "session__user__email")


@admin.register(TechnicianCopilotConfiguration)
class TechnicianCopilotConfigurationAdmin(admin.ModelAdmin):
    list_display = ("company", "is_enabled", "allow_offline_fallback", "updated_at")
    list_filter = ("is_enabled", "allow_offline_fallback")
    search_fields = ("company__name",)


@admin.register(TechnicianCopilotSession)
class TechnicianCopilotSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "site", "service_order", "status", "last_intent", "message_count", "last_activity_at")
    list_filter = ("status", "company", "site", "last_intent")
    search_fields = ("user__email", "service_order__order_number")


@admin.register(TechnicianCopilotMessage)
class TechnicianCopilotMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "role", "detected_intent", "was_offline", "created_at")
    list_filter = ("role", "detected_intent", "was_offline")
    search_fields = ("content", "session__user__email", "session__service_order__order_number")


@admin.register(ClientPortalCopilotConfiguration)
class ClientPortalCopilotConfigurationAdmin(admin.ModelAdmin):
    list_display = ("company", "is_enabled", "updated_at")
    list_filter = ("is_enabled",)
    search_fields = ("company__name",)


@admin.register(ClientPortalCopilotSession)
class ClientPortalCopilotSessionAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "company", "site", "status", "last_intent", "message_count", "last_activity_at")
    list_filter = ("status", "company", "site", "last_intent")
    search_fields = ("title", "user__email", "last_query")


@admin.register(ClientPortalCopilotMessage)
class ClientPortalCopilotMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "role", "detected_intent", "created_at")
    list_filter = ("role", "detected_intent")
    search_fields = ("content", "session__title", "session__user__email")


@admin.register(AIBriefingConfiguration)
class AIBriefingConfigurationAdmin(admin.ModelAdmin):
    list_display = ("company", "is_enabled", "updated_at")
    list_filter = ("is_enabled",)
    search_fields = ("company__name",)


@admin.register(AIBriefing)
class AIBriefingAdmin(admin.ModelAdmin):
    list_display = ("title", "briefing_type", "audience", "company", "site", "user", "status", "generated_at")
    list_filter = ("briefing_type", "audience", "status", "company", "site")
    search_fields = ("title", "summary", "period_label", "user__email")


@admin.register(AIBriefingDelivery)
class AIBriefingDeliveryAdmin(admin.ModelAdmin):
    list_display = ("briefing", "channel", "recipient_user", "status", "delivered_at", "viewed_at")
    list_filter = ("channel", "status")
    search_fields = ("briefing__title", "recipient_user__email")


import logging
logger = logging.getLogger(__name__)

def trigger_n8n_webhook(lead):
    """
    DEPRECATED: marcador legado do fluxo AtlasLead/PendingAtlasLead.

    Mantido sem chamada externa real para compatibilidade com dados antigos.
    Novos fluxos Atlas devem revisar CommercialOpportunity e converter via
    OpportunityBuilderService.convert_to_lead.
    """
    logger.info(f"[ATLAS LEGACY NOOP] Lead legado aprovado no admin: {lead.razao_social} - Email: {lead.email_contato}")


@admin.register(AtlasLead)
class AtlasLeadAdmin(admin.ModelAdmin):
    """DEPRECATED: admin somente para consulta/compatibilidade de AtlasLead legado."""

    list_display = ("razao_social", "cidade", "score", "segmento", "status", "created_at")
    list_filter = ("status", "segmento", "cidade")
    search_fields = ("razao_social", "email_contato", "cidade")
    ordering = ("-score", "-created_at")
    readonly_fields = ("public_id", "created_at", "updated_at")


@admin.register(PendingAtlasLead)
class PendingAtlasLeadAdmin(admin.ModelAdmin):
    """
    DEPRECATED: painel legado de moderação AtlasLead/PendingAtlasLead.

    Mantido apenas para revisão de registros antigos. O fluxo oficial de
    revisão humana Atlas é a tela Admin Shell baseada em CommercialOpportunity.
    """
    list_display = ("razao_social", "cidade", "score", "segmento", "notas_resumo", "status")
    search_fields = ("razao_social", "cidade", "email_contato")
    ordering = ("-score",)
    
    actions = ["approve_selected_leads", "reject_selected_leads"]

    def get_queryset(self, request):
        # Filtro padrão obrigatório
        qs = super().get_queryset(request)
        return qs.filter(status='ready_for_review')
        
    def notas_resumo(self, obj):
        return (obj.notas[:100] + '...') if len(obj.notas) > 100 else obj.notas
    notas_resumo.short_description = "Notas (Fit Comercial / Produtos)"

    @admin.action(description="LEGADO: aprovar AtlasLead selecionado")
    def approve_selected_leads(self, request, queryset):
        approved = 0
        for lead in queryset:
            lead.status = 'approved'
            lead.save()
            trigger_n8n_webhook(lead)
            approved += 1
        self.message_user(request, f"{approved} AtlasLead legados aprovados. Nenhum fluxo novo foi criado.", messages.SUCCESS)

    @admin.action(description="LEGADO: rejeitar/arquivar AtlasLead selecionado")
    def reject_selected_leads(self, request, queryset):
        rejected = queryset.update(status='rejected')
        self.message_user(request, f"{rejected} leads foram rejeitados/arquivados.", messages.WARNING)

