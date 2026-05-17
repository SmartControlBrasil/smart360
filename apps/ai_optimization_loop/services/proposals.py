from decimal import Decimal

from apps.ai_agents_center.models import AgentExecutionPolicy
from apps.ai_decision_engine.models import DecisionPolicy
from apps.ai_optimization_loop.models import DecisionOutcome, OptimizationPolicy, OptimizationProposal, SimulationOutcome
from apps.ai_simulation_engine.models import SimulationType
from apps.observability_center.services.observability_service import SystemEventService

from .audit import OptimizationAuditService
from .policies import OptimizationPolicyService


class OptimizationProposalService:
    @classmethod
    def create_for_decision_outcome(cls, *, outcome: DecisionOutcome):
        decision = outcome.decision
        policy = decision.policy_applied
        if policy is None:
            return None
        if outcome.effectiveness_level not in {"weak", "harmful"}:
            return None
        if policy.requires_human_approval:
            return None
        optimization_policy = OptimizationPolicyService.resolve_policy(
            target_type=OptimizationPolicy.TargetType.DECISION_POLICY,
            proposal_type=OptimizationPolicy.ProposalType.APPROVAL_REQUIREMENT_ADJUSTMENT,
            risk_level=OptimizationPolicy.RiskLevel.HIGH,
        )
        proposal, _ = OptimizationProposal.objects.get_or_create(
            target_type=OptimizationPolicy.TargetType.DECISION_POLICY,
            target_reference=str(policy.public_id),
            proposal_type=OptimizationPolicy.ProposalType.APPROVAL_REQUIREMENT_ADJUSTMENT,
            source_outcome_type="decision_outcome",
            source_outcome_reference=str(outcome.public_id),
            defaults={
                "company": outcome.company,
                "site": outcome.site,
                "current_value": {
                    "requires_human_approval": policy.requires_human_approval,
                    "autonomy_level": policy.autonomy_level,
                    "risk_level": policy.risk_level,
                },
                "proposed_value": {
                    "requires_human_approval": True,
                    "autonomy_level": min(policy.autonomy_level, 1),
                    "risk_level": DecisionPolicy.RiskLevel.HIGH if policy.risk_level == DecisionPolicy.RiskLevel.LOW else policy.risk_level,
                },
                "rationale": "Outcome fraco ou nocivo em policy autoexecutavel sugere retorno de aprovacao humana.",
                "evidence_summary": outcome.evaluation_summary,
                "expected_impact_summary": "Reduzir repeticao de decisoes de baixa efetividade com revisao humana adicional.",
                "risk_level": OptimizationPolicy.RiskLevel.HIGH,
                "policy_applied": optimization_policy,
            },
        )
        cls._log_creation(proposal=proposal)
        return proposal

    @classmethod
    def create_for_simulation_outcome(cls, *, outcome: SimulationOutcome):
        simulation_type = outcome.simulation_run.scenario.simulation_type
        if outcome.effectiveness_level not in {"weak", "harmful"}:
            return None
        current_window = int((simulation_type.heuristics_config or {}).get("observation_window_days", 30))
        proposed_window = min(current_window + 15, 90)
        optimization_policy = OptimizationPolicyService.resolve_policy(
            target_type=OptimizationPolicy.TargetType.SIMULATION_TYPE,
            proposal_type=OptimizationPolicy.ProposalType.HEURISTIC_CONFIG_ADJUSTMENT,
            risk_level=OptimizationPolicy.RiskLevel.MEDIUM,
        )
        proposal, _ = OptimizationProposal.objects.get_or_create(
            target_type=OptimizationPolicy.TargetType.SIMULATION_TYPE,
            target_reference=str(simulation_type.public_id),
            proposal_type=OptimizationPolicy.ProposalType.HEURISTIC_CONFIG_ADJUSTMENT,
            source_outcome_type="simulation_outcome",
            source_outcome_reference=str(outcome.public_id),
            defaults={
                "company": outcome.company,
                "site": outcome.site,
                "current_value": {"heuristics_config": simulation_type.heuristics_config, "policy_mode": simulation_type.policy_mode},
                "proposed_value": {
                    "heuristics_config": {"observation_window_days": proposed_window, "confidence_guardrail": True},
                },
                "rationale": "Baixa aderencia entre simulacao prevista e resultado observado sugere ampliar janela de observacao e guardrail de confianca.",
                "evidence_summary": outcome.evaluation_summary,
                "expected_impact_summary": "Melhorar aderencia entre impacto previsto e realizado nas proximas simulacoes.",
                "risk_level": OptimizationPolicy.RiskLevel.MEDIUM,
                "policy_applied": optimization_policy,
            },
        )
        cls._log_creation(proposal=proposal)
        return proposal

    @classmethod
    def create_for_agent_policy(cls, *, execution_policy: AgentExecutionPolicy, company=None, site=None, evidence_summary="", score=None):
        current_max = execution_policy.max_recommendations
        if current_max <= 3:
            return None
        optimization_policy = OptimizationPolicyService.resolve_policy(
            target_type=OptimizationPolicy.TargetType.AGENT_EXECUTION_POLICY,
            proposal_type=OptimizationPolicy.ProposalType.RANKING_ADJUSTMENT,
            risk_level=OptimizationPolicy.RiskLevel.MEDIUM,
        )
        proposal, _ = OptimizationProposal.objects.get_or_create(
            target_type=OptimizationPolicy.TargetType.AGENT_EXECUTION_POLICY,
            target_reference=str(execution_policy.agent.public_id),
            proposal_type=OptimizationPolicy.ProposalType.RANKING_ADJUSTMENT,
            source_outcome_type="agent_quality",
            source_outcome_reference=execution_policy.agent.slug,
            defaults={
                "company": company,
                "site": site,
                "current_value": {"max_recommendations": current_max, "config": execution_policy.config},
                "proposed_value": {"max_recommendations": max(current_max - 2, 3)},
                "rationale": "Baixa efetividade agregada sugere reduzir volume e aumentar precisao das recomendacoes entregues.",
                "evidence_summary": evidence_summary,
                "expected_impact_summary": f"Priorizar sinais de maior qualidade para o agente {execution_policy.agent.slug}.",
                "risk_level": OptimizationPolicy.RiskLevel.MEDIUM,
                "policy_applied": optimization_policy,
                "metadata": {"quality_score": str(score) if score is not None else ""},
            },
        )
        cls._log_creation(proposal=proposal)
        return proposal

    @staticmethod
    def _log_creation(*, proposal):
        if proposal is None:
            return
        OptimizationAuditService.log_event(
            proposal=proposal,
            event_type="optimization.proposal.created",
            message="Optimization proposal created.",
            payload={"target_type": proposal.target_type, "proposal_type": proposal.proposal_type},
        )
        SystemEventService.log_system_event(
            event_type="optimization.proposal.created",
            source_module="ai_optimization_loop",
            message="Optimization proposal created.",
            entity_type=proposal.target_type,
            entity_id=proposal.target_reference,
            company=proposal.company,
            site=proposal.site,
            payload={"proposal_public_id": str(proposal.public_id), "proposal_type": proposal.proposal_type},
        )

