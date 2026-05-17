from django.db import transaction

from apps.ai_agents_center.models import AgentExecutionPolicy, AgentRecommendation
from apps.ai_experimentation_framework.models import ExperimentAssignment
from apps.ai_experimentation_framework.services.engine import ExperimentationEngine
from apps.ai_optimization_loop.models import FeedbackSignal, OptimizationProposal
from apps.observability_center.services.observability_service import SystemEventService

from .feedback import FeedbackSignalService
from .outcomes import DecisionOutcomeService, RecommendationOutcomeService, SimulationOutcomeService
from .proposals import OptimizationProposalService
from .quality import OptimizationQualityService


class LearningOrchestrator:
    @staticmethod
    def _assignment_from_payload(payload: dict):
        experiment_payload = (payload or {}).get("experiment", {})
        assignment_public_id = experiment_payload.get("assignment_public_id")
        if not assignment_public_id:
            return None
        return ExperimentAssignment.objects.select_related("experiment", "variant").filter(public_id=assignment_public_id).first()

    @classmethod
    @transaction.atomic
    def measure_recommendation(cls, *, recommendation: AgentRecommendation):
        outcome = RecommendationOutcomeService.measure(recommendation=recommendation)
        assignment = cls._assignment_from_payload(recommendation.agent_run.input_context or {})
        if assignment is not None:
            ExperimentationEngine.record_assignment_metric(
                assignment=assignment,
                metric_type="recommendation_effectiveness_score",
                value=outcome.effectiveness_score,
                unit="score",
                source_component="ai_optimization_loop",
                source_reference=str(recommendation.public_id),
                metadata={"effectiveness_level": outcome.effectiveness_level},
            )
        return outcome

    @classmethod
    @transaction.atomic
    def measure_decision(cls, *, decision, execution=None):
        outcome = DecisionOutcomeService.measure(decision=decision, execution=execution)
        assignment = cls._assignment_from_payload(decision.explainability_payload or {})
        if assignment is not None:
            ExperimentationEngine.record_assignment_metric(
                assignment=assignment,
                metric_type="decision_effectiveness_score",
                value=outcome.effectiveness_score,
                unit="score",
                source_component="ai_optimization_loop",
                source_reference=str(decision.public_id),
                metadata={"effectiveness_level": outcome.effectiveness_level, "result_status": outcome.result_status},
            )
        proposal = OptimizationProposalService.create_for_decision_outcome(outcome=outcome)
        for simulation_run in decision.simulation_runs.select_related("scenario", "scenario__simulation_type", "result"):
            cls.measure_simulation(simulation_run=simulation_run)
        return outcome, proposal

    @classmethod
    @transaction.atomic
    def measure_simulation(cls, *, simulation_run):
        outcome = SimulationOutcomeService.measure(simulation_run=simulation_run)
        assignment = ExperimentationEngine.resolve_assignment(
            target_component="simulation_engine",
            target_reference=simulation_run.scenario.simulation_type.slug,
            entity_key=str(simulation_run.public_id),
            entity_type="simulation_run",
            company=simulation_run.scenario.company,
            site=simulation_run.scenario.site,
            context={"source_type": simulation_run.source_type},
        )
        if assignment is not None:
            ExperimentationEngine.record_assignment_metric(
                assignment=assignment,
                metric_type="simulation_effectiveness_score",
                value=outcome.effectiveness_score,
                unit="score",
                source_component="ai_optimization_loop",
                source_reference=str(simulation_run.public_id),
                metadata={"effectiveness_level": outcome.effectiveness_level, "result_status": outcome.result_status},
            )
        proposal = OptimizationProposalService.create_for_simulation_outcome(outcome=outcome)
        return outcome, proposal

    @classmethod
    @transaction.atomic
    def register_feedback(
        cls,
        *,
        source_type,
        source_reference,
        signal_type,
        score,
        company=None,
        site=None,
        user=None,
        comment="",
        metadata=None,
    ):
        feedback = FeedbackSignalService.register(
            source_type=source_type,
            source_reference=source_reference,
            signal_type=signal_type,
            score=score,
            company=company,
            site=site,
            user=user,
            comment=comment,
            metadata=metadata,
        )
        if source_type == FeedbackSignal.SourceType.RECOMMENDATION:
            recommendation = AgentRecommendation.objects.select_related("company", "site").get(public_id=source_reference)
            RecommendationOutcomeService.measure(recommendation=recommendation)
        elif source_type == FeedbackSignal.SourceType.DECISION:
            from apps.ai_decision_engine.models import AgentDecision

            decision = AgentDecision.objects.select_related("company", "site", "policy_applied").get(public_id=source_reference)
            cls.measure_decision(decision=decision)
        elif source_type == FeedbackSignal.SourceType.SIMULATION:
            from apps.ai_simulation_engine.models import SimulationRun

            simulation_run = SimulationRun.objects.select_related("scenario", "scenario__simulation_type", "result", "decision").get(public_id=source_reference)
            cls.measure_simulation(simulation_run=simulation_run)
        return feedback

    @classmethod
    def generate_company_proposals(cls, *, company=None, site=None):
        generated = []
        for row in OptimizationQualityService.agent_quality(company=company):
            if row["composite_score"] and row["composite_score"] < 45:
                execution_policy = AgentExecutionPolicy.objects.select_related("agent").filter(agent__slug=row["agent_slug"]).first()
                if execution_policy is not None:
                    proposal = OptimizationProposalService.create_for_agent_policy(
                        execution_policy=execution_policy,
                        company=company,
                        site=site,
                        evidence_summary=f"Composite quality score {row['composite_score']:.2f} for agent {row['agent_slug']}.",
                        score=row["composite_score"],
                    )
                    if proposal is not None:
                        generated.append(proposal)
        SystemEventService.log_system_event(
            event_type="optimization.proposal.created",
            source_module="ai_optimization_loop",
            message="Batch optimization generation executed.",
            entity_type="optimization_batch",
            entity_id=str(company.id) if company else "global",
            company=company,
            site=site,
            payload={"generated_count": len(generated)},
        )
        return generated
