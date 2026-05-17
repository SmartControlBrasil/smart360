from apps.ai_decision_engine.models import AgentDecision
from apps.ai_simulation_engine.models import SimulationRun, SimulationType

from .policies import SimulationPolicyService


class SimulationDecisionSupportService:
    @classmethod
    def get_requirement(cls, *, decision: AgentDecision):
        requirement = SimulationPolicyService.get_requirement_for_decision(decision)
        if requirement is None:
            return None
        simulation_type = SimulationType.objects.filter(slug=requirement["simulation_type"]).first()
        return {
            "simulation_type": requirement["simulation_type"],
            "mode": requirement["mode"],
            "label": simulation_type.name if simulation_type else requirement["simulation_type"],
        }

    @classmethod
    def latest_completed_run(cls, *, decision: AgentDecision):
        return decision.simulation_runs.filter(status=SimulationRun.RunStatus.COMPLETED).select_related("result", "scenario", "scenario__simulation_type").order_by("-created_at").first()

    @classmethod
    def simulation_satisfies_requirement(cls, *, decision: AgentDecision):
        requirement = cls.get_requirement(decision=decision)
        if requirement is None:
            return True, None
        latest = cls.latest_completed_run(decision=decision)
        if latest and latest.scenario.simulation_type.slug == requirement["simulation_type"]:
            return True, latest
        if requirement["mode"] == SimulationType.PolicyMode.REQUIRED:
            return False, latest
        return True, latest

