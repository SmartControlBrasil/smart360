from dataclasses import dataclass

from apps.ai_decision_engine.models import DecisionPolicy


@dataclass(frozen=True)
class ActionCatalogEntry:
    action_type: str
    aliases: tuple[str, ...]
    risk_level: str
    autonomy_level: int
    tenant_scope_mode: str
    rollback_required: bool
    supports_execution: bool
    requires_human_approval: bool
    approver_role_slugs: tuple[str, ...]
    description: str


ACTION_CATALOG: dict[str, ActionCatalogEntry] = {
    "create_work_order_proposal": ActionCatalogEntry(
        action_type="create_work_order_proposal",
        aliases=("open_inspection_work_order",),
        risk_level="high",
        autonomy_level=1,
        tenant_scope_mode=DecisionPolicy.TenantScopeMode.SITE,
        rollback_required=False,
        supports_execution=True,
        requires_human_approval=True,
        approver_role_slugs=("maintenance-manager", "company-admin", "super-admin"),
        description="Materializa uma ordem de servico controlada.",
    ),
    "create_preventive_review_task": ActionCatalogEntry(
        action_type="create_preventive_review_task",
        aliases=("review_preventive_plan", "reevaluate_preventive_frequency", "prioritize_preventive_to_reduce_corrective_cost"),
        risk_level="medium",
        autonomy_level=1,
        tenant_scope_mode=DecisionPolicy.TenantScopeMode.SITE,
        rollback_required=False,
        supports_execution=True,
        requires_human_approval=True,
        approver_role_slugs=("maintenance-manager", "company-admin", "super-admin"),
        description="Abre uma revisao preventiva ou OS de acompanhamento.",
    ),
    "mark_asset_attention": ActionCatalogEntry(
        action_type="mark_asset_attention",
        aliases=("mark_asset_under_watch",),
        risk_level="low",
        autonomy_level=2,
        tenant_scope_mode=DecisionPolicy.TenantScopeMode.SITE,
        rollback_required=True,
        supports_execution=True,
        requires_human_approval=False,
        approver_role_slugs=("maintenance-manager", "company-admin", "super-admin"),
        description="Atualiza flag de watchlist do ativo.",
    ),
    "create_schedule_adjustment_proposal": ActionCatalogEntry(
        action_type="create_schedule_adjustment_proposal",
        aliases=("reassign_visits_between_technicians", "move_visit_to_earlier_slot", "schedule_unassigned_visit", "block_schedule_for_review"),
        risk_level="high",
        autonomy_level=1,
        tenant_scope_mode=DecisionPolicy.TenantScopeMode.SITE,
        rollback_required=True,
        supports_execution=True,
        requires_human_approval=True,
        approver_role_slugs=("coordinator", "company-admin", "super-admin"),
        description="Cria ajuste controlado de agenda ou priorizacao de visita.",
    ),
    "reorder_route_proposal": ActionCatalogEntry(
        action_type="reorder_route_proposal",
        aliases=("reorder_route_plan", "suggest_route_consolidation"),
        risk_level="medium",
        autonomy_level=1,
        tenant_scope_mode=DecisionPolicy.TenantScopeMode.SITE,
        rollback_required=True,
        supports_execution=True,
        requires_human_approval=True,
        approver_role_slugs=("coordinator", "company-admin", "super-admin"),
        description="Reordena rota em modo auditado.",
    ),
    "assign_marketplace_candidate_proposal": ActionCatalogEntry(
        action_type="assign_marketplace_candidate_proposal",
        aliases=("assign_recommended_marketplace_technician", "suggest_alternative_technician_via_matching"),
        risk_level="high",
        autonomy_level=1,
        tenant_scope_mode=DecisionPolicy.TenantScopeMode.COMPANY,
        rollback_required=True,
        supports_execution=True,
        requires_human_approval=True,
        approver_role_slugs=("coordinator", "company-admin", "super-admin"),
        description="Aloca tecnico marketplace sob aprovacao.",
    ),
    "flag_contract_profitability_attention": ActionCatalogEntry(
        action_type="flag_contract_profitability_attention",
        aliases=("review_client_in_management_committee", "suggest_contract_repricing", "review_contract_profitability_shift"),
        risk_level="medium",
        autonomy_level=2,
        tenant_scope_mode=DecisionPolicy.TenantScopeMode.COMPANY,
        rollback_required=True,
        supports_execution=True,
        requires_human_approval=False,
        approver_role_slugs=("commercial-manager", "company-admin", "super-admin"),
        description="Materializa flag de rentabilidade e comercial.",
    ),
    "create_investigation_task": ActionCatalogEntry(
        action_type="create_investigation_task",
        aliases=(
            "create_technical_analysis",
            "review_checklist_strategy",
            "trigger_maintenance_specialist_review",
            "open_operational_investigation",
            "review_parts_consumption",
        ),
        risk_level="low",
        autonomy_level=2,
        tenant_scope_mode=DecisionPolicy.TenantScopeMode.SITE,
        rollback_required=False,
        supports_execution=True,
        requires_human_approval=False,
        approver_role_slugs=("maintenance-manager", "coordinator", "company-admin", "super-admin"),
        description="Abre tarefa segura de investigacao ou inspecao.",
    ),
    "escalate_operational_alert": ActionCatalogEntry(
        action_type="escalate_operational_alert",
        aliases=("open_operational_attention_committee", "review_marketplace_regional_coverage", "activate_marketplace_fallback", "reassess_candidate_due_unavailability"),
        risk_level="medium",
        autonomy_level=1,
        tenant_scope_mode=DecisionPolicy.TenantScopeMode.SITE,
        rollback_required=False,
        supports_execution=True,
        requires_human_approval=True,
        approver_role_slugs=("coordinator", "maintenance-manager", "company-admin", "super-admin"),
        description="Escala alerta operacional para fila formal e auditada.",
    ),
    "review_commercial_opportunity": ActionCatalogEntry(
        action_type="review_commercial_opportunity",
        aliases=(),
        risk_level="medium",
        autonomy_level=1,
        tenant_scope_mode=DecisionPolicy.TenantScopeMode.COMPANY,
        rollback_required=False,
        supports_execution=True,
        requires_human_approval=True,
        approver_role_slugs=("commercial-manager", "company-admin", "super-admin"),
        description="Revisao de oportunidade comercial do Atlas.",
    ),
    "enrich_commercial_opportunity": ActionCatalogEntry(
        action_type="enrich_commercial_opportunity",
        aliases=(),
        risk_level="low",
        autonomy_level=2,
        tenant_scope_mode=DecisionPolicy.TenantScopeMode.COMPANY,
        rollback_required=False,
        supports_execution=True,
        requires_human_approval=False,
        approver_role_slugs=("commercial-manager", "company-admin", "super-admin"),
        description="Enriquecimento de oportunidade comercial do Atlas.",
    ),
    "convert_commercial_opportunity_to_lead": ActionCatalogEntry(
        action_type="convert_commercial_opportunity_to_lead",
        aliases=(),
        risk_level="high",
        autonomy_level=1,
        tenant_scope_mode=DecisionPolicy.TenantScopeMode.COMPANY,
        rollback_required=False,
        supports_execution=True,
        requires_human_approval=True,
        approver_role_slugs=("commercial-manager", "company-admin", "super-admin"),
        description="Converte oportunidade comercial aprovada em Lead oficial.",
    ),
}


ALIAS_LOOKUP = {
    alias: entry.action_type
    for entry in ACTION_CATALOG.values()
    for alias in entry.aliases
}

