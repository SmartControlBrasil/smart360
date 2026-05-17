from apps.ai_decision_engine.models import AgentDecision
from apps.ai_simulation_engine.models import SimulationType


SIMULATION_REQUIREMENT_BY_ACTION = {
    "reorder_route_proposal": ("route_reorder_simulation", SimulationType.PolicyMode.RECOMMENDED),
    "create_schedule_adjustment_proposal": ("technician_reassignment_simulation", SimulationType.PolicyMode.RECOMMENDED),
    "create_preventive_review_task": ("preventive_frequency_change_simulation", SimulationType.PolicyMode.REQUIRED),
    "flag_contract_profitability_attention": ("contract_repricing_simulation", SimulationType.PolicyMode.REQUIRED),
    "assign_marketplace_candidate_proposal": ("marketplace_candidate_swap_simulation", SimulationType.PolicyMode.RECOMMENDED),
    "create_work_order_proposal": ("maintenance_action_plan_simulation", SimulationType.PolicyMode.REQUIRED),
    "create_investigation_task": ("maintenance_action_plan_simulation", SimulationType.PolicyMode.RECOMMENDED),
    "mark_asset_attention": ("maintenance_action_plan_simulation", SimulationType.PolicyMode.RECOMMENDED),
}


class SimulationPolicyService:
    @classmethod
    def get_requirement_for_decision(cls, decision: AgentDecision):
        required = SIMULATION_REQUIREMENT_BY_ACTION.get(decision.normalized_action_type)
        if required:
            return {"simulation_type": required[0], "mode": required[1]}
        return None

