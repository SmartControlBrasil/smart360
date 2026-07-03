from dataclasses import dataclass


@dataclass(frozen=True)
class AutonomousActionRule:
    action_type: str
    default_threshold: float
    requires_simulation: bool
    rollback_supported: bool
    max_risk_level: str
    description: str


ELIGIBLE_ACTIONS: dict[str, AutonomousActionRule] = {
    "mark_asset_attention": AutonomousActionRule("mark_asset_attention", 0.70, False, True, "low", "Flag interna reversivel de ativo em atencao."),
    "create_investigation_task": AutonomousActionRule("create_investigation_task", 0.72, False, False, "low", "Investigacao interna segura e auditada."),
    "flag_contract_profitability_attention": AutonomousActionRule("flag_contract_profitability_attention", 0.78, False, True, "medium", "Watch interno de rentabilidade."),
    "reorder_route_proposal": AutonomousActionRule("reorder_route_proposal", 0.85, True, True, "medium", "Reordena rota segura com simulacao previa."),
    "enrich_commercial_opportunity": AutonomousActionRule("enrich_commercial_opportunity", 0.70, False, False, "low", "Enriquecimento comercial deterministico sem chamada externa."),
}

BLOCKED_ACTIONS = {
    "create_work_order_proposal",
    "create_schedule_adjustment_proposal",
    "assign_marketplace_candidate_proposal",
    "escalate_operational_alert",
    "review_commercial_opportunity",
    "convert_commercial_opportunity_to_lead",
}

