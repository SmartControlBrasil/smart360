from django.utils import timezone

from apps.ai_agents_center.models import AgentExecutionPolicy, ManagerCopilotConfiguration
from apps.ai_decision_engine.models import DecisionPolicy
from apps.ai_optimization_loop.models import OptimizationProposal
from apps.ai_simulation_engine.models import SimulationType

from .audit import OptimizationAuditService


class OptimizationApplierService:
    @classmethod
    def apply(cls, *, proposal: OptimizationProposal, applied_by_mode, actor_user=None):
        if proposal.target_type == "agent_execution_policy":
            target = AgentExecutionPolicy.objects.select_related("agent").get(agent__public_id=proposal.target_reference)
            if "max_recommendations" in proposal.proposed_value:
                target.max_recommendations = proposal.proposed_value["max_recommendations"]
            if "config" in proposal.proposed_value:
                target.config = {**(target.config or {}), **proposal.proposed_value["config"]}
            target.save(update_fields=["max_recommendations", "config", "updated_at"])
        elif proposal.target_type == "decision_policy":
            target = DecisionPolicy.objects.get(public_id=proposal.target_reference)
            update_fields = []
            for field_name in ("requires_human_approval", "autonomy_level", "risk_level"):
                if field_name in proposal.proposed_value:
                    setattr(target, field_name, proposal.proposed_value[field_name])
                    update_fields.append(field_name)
            if "config" in proposal.proposed_value:
                target.config = {**(target.config or {}), **proposal.proposed_value["config"]}
                update_fields.append("config")
            target.save(update_fields=[*update_fields, "updated_at"])
        elif proposal.target_type == "simulation_type":
            target = SimulationType.objects.get(public_id=proposal.target_reference)
            update_fields = []
            if "policy_mode" in proposal.proposed_value:
                target.policy_mode = proposal.proposed_value["policy_mode"]
                update_fields.append("policy_mode")
            if "heuristics_config" in proposal.proposed_value:
                target.heuristics_config = {**(target.heuristics_config or {}), **proposal.proposed_value["heuristics_config"]}
                update_fields.append("heuristics_config")
            target.save(update_fields=[*update_fields, "updated_at"])
        elif proposal.target_type == "copilot_configuration":
            target = ManagerCopilotConfiguration.objects.get(public_id=proposal.target_reference)
            if "behavior_config" in proposal.proposed_value:
                target.behavior_config = {**(target.behavior_config or {}), **proposal.proposed_value["behavior_config"]}
                target.save(update_fields=["behavior_config", "updated_at"])
        else:
            raise ValueError(f"Unsupported optimization target: {proposal.target_type}")
        proposal.status = OptimizationProposal.Status.APPLIED
        proposal.applied_by_mode = applied_by_mode
        proposal.applied_at = timezone.now()
        proposal.save(update_fields=["status", "applied_by_mode", "applied_at", "updated_at"])
        OptimizationAuditService.log_event(
            proposal=proposal,
            actor_user=actor_user,
            event_type="optimization.adjustment.applied",
            message="Optimization adjustment applied.",
            payload={"target_type": proposal.target_type, "target_reference": proposal.target_reference},
        )
        return proposal
