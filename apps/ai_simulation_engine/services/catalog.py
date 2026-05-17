from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationCatalogEntry:
    simulation_type: str
    aliases: tuple[str, ...]
    target_actions: tuple[str, ...]
    optional_metrics: tuple[str, ...]


SIMULATION_CATALOG: dict[str, SimulationCatalogEntry] = {
    "route_reorder_simulation": SimulationCatalogEntry(
        simulation_type="route_reorder_simulation",
        aliases=("reorder_route_proposal", "reorder_route_plan"),
        target_actions=("reorder_route_proposal",),
        optional_metrics=("travel_delta", "sla_delta", "workload_delta"),
    ),
    "technician_reassignment_simulation": SimulationCatalogEntry(
        simulation_type="technician_reassignment_simulation",
        aliases=("create_schedule_adjustment_proposal", "reassign_visits_between_technicians", "move_visit_to_earlier_slot"),
        target_actions=("create_schedule_adjustment_proposal",),
        optional_metrics=("sla_delta", "travel_delta", "workload_delta"),
    ),
    "preventive_frequency_change_simulation": SimulationCatalogEntry(
        simulation_type="preventive_frequency_change_simulation",
        aliases=("create_preventive_review_task", "review_preventive_plan", "reevaluate_preventive_frequency"),
        target_actions=("create_preventive_review_task",),
        optional_metrics=("cost_delta", "risk_delta", "workload_delta"),
    ),
    "contract_repricing_simulation": SimulationCatalogEntry(
        simulation_type="contract_repricing_simulation",
        aliases=("flag_contract_profitability_attention", "suggest_contract_repricing"),
        target_actions=("flag_contract_profitability_attention",),
        optional_metrics=("profit_delta", "cost_delta", "risk_delta"),
    ),
    "route_consolidation_simulation": SimulationCatalogEntry(
        simulation_type="route_consolidation_simulation",
        aliases=("suggest_route_consolidation",),
        target_actions=("reorder_route_proposal",),
        optional_metrics=("travel_delta", "cost_delta", "workload_delta"),
    ),
    "workload_redistribution_simulation": SimulationCatalogEntry(
        simulation_type="workload_redistribution_simulation",
        aliases=("workload_redistribution",),
        target_actions=("create_schedule_adjustment_proposal",),
        optional_metrics=("workload_delta", "sla_delta"),
    ),
    "marketplace_candidate_swap_simulation": SimulationCatalogEntry(
        simulation_type="marketplace_candidate_swap_simulation",
        aliases=("assign_marketplace_candidate_proposal", "suggest_alternative_technician_via_matching"),
        target_actions=("assign_marketplace_candidate_proposal",),
        optional_metrics=("sla_delta", "travel_delta", "risk_delta"),
    ),
    "maintenance_action_plan_simulation": SimulationCatalogEntry(
        simulation_type="maintenance_action_plan_simulation",
        aliases=("create_investigation_task", "create_work_order_proposal", "mark_asset_attention"),
        target_actions=("create_investigation_task", "create_work_order_proposal", "mark_asset_attention"),
        optional_metrics=("risk_delta", "cost_delta", "workload_delta"),
    ),
}

