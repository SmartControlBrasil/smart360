from decimal import Decimal

from django.db.models import Avg
from django.utils import timezone

from apps.ai_agents_center.models import AgentRecommendation, ManagerCopilotMessage
from apps.ai_decision_engine.models import AgentDecision, DecisionExecution
from apps.ai_optimization_loop.models import DecisionOutcome, FeedbackSignal, RecommendationOutcome, SimulationOutcome
from apps.ai_simulation_engine.models import SimulationRun
from apps.marketplace_technicians.models import TechnicianAssignment
from apps.observability_center.services.observability_service import SystemEventService
from apps.smart_system.models import AssetHistoryEvent, FailureEvent, RoutePlan, ScheduledVisit, ServiceOrder

from .feedback import FeedbackSignalService
from .scoring import EffectivenessScoringService


def _feedback_avg(source_type, source_reference):
    value = FeedbackSignal.objects.filter(source_type=source_type, source_reference=str(source_reference)).aggregate(avg=Avg("score"))["avg"]
    return value


class RecommendationOutcomeService:
    @classmethod
    def measure(cls, *, recommendation: AgentRecommendation):
        base_score = Decimal("40.00")
        outcome_status = RecommendationOutcome.OutcomeStatus.PENDING
        observed_summary = "Recommendation still awaiting explicit adoption signal."
        if recommendation.status == AgentRecommendation.Status.APPLIED:
            base_score = Decimal("85.00")
            outcome_status = RecommendationOutcome.OutcomeStatus.APPLIED
            observed_summary = "Recommendation was applied by operations."
        elif recommendation.status == AgentRecommendation.Status.ACCEPTED:
            base_score = Decimal("72.00")
            outcome_status = RecommendationOutcome.OutcomeStatus.OBSERVED
            observed_summary = "Recommendation accepted and queued for action."
        elif recommendation.status == AgentRecommendation.Status.REVIEWED:
            base_score = Decimal("55.00")
            outcome_status = RecommendationOutcome.OutcomeStatus.OBSERVED
            observed_summary = "Recommendation was reviewed and remained relevant."
        elif recommendation.status == AgentRecommendation.Status.DISMISSED:
            base_score = Decimal("18.00")
            outcome_status = RecommendationOutcome.OutcomeStatus.DISMISSED
            observed_summary = "Recommendation was dismissed by the operator."
        feedback_average = _feedback_avg(FeedbackSignal.SourceType.RECOMMENDATION, recommendation.public_id)
        effectiveness_score = EffectivenessScoringService.apply_feedback_adjustment(base_score=base_score, feedback_average=feedback_average)
        effectiveness_level = EffectivenessScoringService.classify(effectiveness_score)
        outcome, _ = RecommendationOutcome.objects.update_or_create(
            recommendation=recommendation,
            defaults={
                "company": recommendation.company,
                "site": recommendation.site,
                "outcome_status": outcome_status,
                "expected_effect_summary": recommendation.suggested_action or recommendation.summary,
                "observed_effect_summary": observed_summary,
                "effectiveness_score": effectiveness_score,
                "effectiveness_level": effectiveness_level,
                "comparison_payload": {
                    "status": recommendation.status,
                    "attention_score": recommendation.attention_score,
                    "feedback_average": str(feedback_average) if feedback_average is not None else "",
                },
                "measured_at": timezone.now(),
            },
        )
        SystemEventService.log_system_event(
            event_type="optimization.outcome.measured",
            source_module="ai_optimization_loop",
            message="Recommendation outcome measured.",
            entity_type="recommendation",
            entity_id=str(recommendation.public_id),
            company=recommendation.company,
            site=recommendation.site,
            payload={"effectiveness_score": str(effectiveness_score), "effectiveness_level": effectiveness_level},
        )
        return outcome


class DecisionOutcomeService:
    @classmethod
    def _artifact_bonus(cls, *, decision: AgentDecision, execution: DecisionExecution | None):
        if execution is None or execution.execution_status != DecisionExecution.ExecutionStatus.SUCCEEDED:
            return Decimal("0.00"), {}
        payload = execution.result_payload or {}
        artifacts = {}
        bonus = Decimal("0.00")
        if decision.normalized_action_type == "create_work_order_proposal" and payload.get("order_number"):
            order_exists = ServiceOrder.objects.filter(public_id=execution.decision.execution_payload.get("related_entity_id")).exists()
            artifacts["service_order_created"] = order_exists
            if order_exists:
                bonus += Decimal("15.00")
        elif decision.normalized_action_type == "create_schedule_adjustment_proposal" and payload.get("visit_public_id"):
            visit = ScheduledVisit.objects.filter(public_id=payload["visit_public_id"]).first()
            artifacts["visit_scheduled"] = bool(visit and visit.technician_schedule_id)
            if artifacts["visit_scheduled"]:
                bonus += Decimal("12.00")
        elif decision.normalized_action_type == "reorder_route_proposal" and payload.get("route_plan_public_id"):
            artifacts["route_plan_created"] = RoutePlan.objects.filter(public_id=payload["route_plan_public_id"]).exists()
            if artifacts["route_plan_created"]:
                bonus += Decimal("8.00")
        elif decision.normalized_action_type == "assign_marketplace_candidate_proposal" and payload.get("assignment_public_id"):
            artifacts["assignment_created"] = TechnicianAssignment.objects.filter(public_id=payload["assignment_public_id"]).exists()
            if artifacts["assignment_created"]:
                bonus += Decimal("12.00")
        elif decision.normalized_action_type == "create_investigation_task":
            event_public_id = payload.get("failure_event_public_id") or payload.get("history_event_public_id")
            artifacts["investigation_recorded"] = FailureEvent.objects.filter(public_id=event_public_id).exists() or AssetHistoryEvent.objects.filter(public_id=event_public_id).exists()
            if artifacts["investigation_recorded"]:
                bonus += Decimal("12.00")
        elif decision.normalized_action_type == "mark_asset_attention" and payload.get("flag_public_id"):
            artifacts["flag_materialized"] = True
            bonus += Decimal("15.00")
        return bonus, artifacts

    @classmethod
    def measure(cls, *, decision: AgentDecision, execution: DecisionExecution | None = None):
        execution = execution or decision.executions.order_by("-created_at").first()
        if execution is None:
            base_score = Decimal("35.00")
            result_status = DecisionOutcome.ResultStatus.PENDING
            execution_status = ""
            actual_result = {"status": "not_executed"}
            evaluation_summary = "Decision still has no execution trace."
        elif execution.execution_status == DecisionExecution.ExecutionStatus.SUCCEEDED:
            base_score = Decimal("70.00")
            result_status = DecisionOutcome.ResultStatus.SUCCEEDED
            execution_status = execution.execution_status
            actual_result = {
                "execution_summary": execution.execution_summary,
                "result_payload": execution.result_payload,
                "duration_ms": execution.duration_ms,
            }
            evaluation_summary = "Decision executed successfully with observable operational artifact."
        else:
            base_score = Decimal("12.00")
            result_status = DecisionOutcome.ResultStatus.FAILED
            execution_status = execution.execution_status
            actual_result = {"error_message": execution.error_message, "result_payload": execution.result_payload}
            evaluation_summary = "Decision execution failed and produced negative learning signal."
        artifact_bonus, artifacts = cls._artifact_bonus(decision=decision, execution=execution)
        feedback_average = _feedback_avg(FeedbackSignal.SourceType.DECISION, decision.public_id)
        effectiveness_score = EffectivenessScoringService.apply_feedback_adjustment(
            base_score=base_score + artifact_bonus,
            feedback_average=feedback_average,
        )
        effectiveness_level = EffectivenessScoringService.classify(effectiveness_score)
        expected_result = {
            "decision_reason": decision.decision_reason,
            "simulation_summary": (decision.explainability_payload or {}).get("simulation", {}).get("summary", ""),
            "policy": getattr(decision.policy_applied, "slug", ""),
        }
        outcome, _ = DecisionOutcome.objects.update_or_create(
            decision=decision,
            defaults={
                "company": decision.company,
                "site": decision.site,
                "execution_status": execution_status,
                "result_status": result_status,
                "expected_result": expected_result,
                "actual_result": {**actual_result, "artifacts": artifacts},
                "effectiveness_score": effectiveness_score,
                "effectiveness_level": effectiveness_level,
                "evaluation_summary": evaluation_summary,
                "measured_at": timezone.now(),
            },
        )
        FeedbackSignalService.register(
            source_type=FeedbackSignal.SourceType.DECISION,
            source_reference=decision.public_id,
            signal_type=FeedbackSignal.SignalType.IMPLICIT_OPERATIONAL,
            score=effectiveness_score,
            company=decision.company,
            site=decision.site,
            user=None,
            comment=evaluation_summary,
            metadata={"effectiveness_level": effectiveness_level, "artifacts": artifacts},
        )
        SystemEventService.log_system_event(
            event_type="optimization.effectiveness.scored",
            source_module="ai_optimization_loop",
            message="Decision effectiveness scored.",
            entity_type="decision",
            entity_id=str(decision.public_id),
            company=decision.company,
            site=decision.site,
            payload={"effectiveness_score": str(effectiveness_score), "effectiveness_level": effectiveness_level},
        )
        return outcome


class SimulationOutcomeService:
    @classmethod
    def measure(cls, *, simulation_run: SimulationRun):
        result = getattr(simulation_run, "result", None)
        decision = simulation_run.decision
        expected_result = {
            "summary": getattr(result, "summary", ""),
            "impact_score": str(getattr(result, "impact_score", "")),
            "payload": getattr(result, "result_payload", {}),
        }
        if decision and hasattr(decision, "optimization_outcome"):
            decision_outcome = decision.optimization_outcome
            actual_result = {
                "decision_result_status": decision_outcome.result_status,
                "decision_effectiveness_score": str(decision_outcome.effectiveness_score),
                "decision_summary": decision_outcome.evaluation_summary,
            }
            base_score = decision_outcome.effectiveness_score
            result_status = SimulationOutcome.ResultStatus.OBSERVED if decision_outcome.result_status == DecisionOutcome.ResultStatus.SUCCEEDED else SimulationOutcome.ResultStatus.DIVERGED
        elif decision and decision.decision_status in {AgentDecision.DecisionStatus.REJECTED, AgentDecision.DecisionStatus.AUTO_BLOCKED}:
            actual_result = {"decision_status": decision.decision_status}
            base_score = Decimal("45.00")
            result_status = SimulationOutcome.ResultStatus.NOT_EXECUTED
        else:
            actual_result = {"decision_status": getattr(decision, "decision_status", "pending")}
            base_score = Decimal("45.00")
            result_status = SimulationOutcome.ResultStatus.PENDING
        confidence = getattr(result, "confidence_level", "medium")
        if confidence == "high" and base_score < Decimal("45.00"):
            base_score -= Decimal("10.00")
        feedback_average = _feedback_avg(FeedbackSignal.SourceType.SIMULATION, simulation_run.public_id)
        effectiveness_score = EffectivenessScoringService.apply_feedback_adjustment(base_score=base_score, feedback_average=feedback_average)
        effectiveness_level = EffectivenessScoringService.classify(effectiveness_score)
        summary = "Simulation tracked against observed execution result." if decision else "Simulation still awaiting observed execution."
        outcome, _ = SimulationOutcome.objects.update_or_create(
            simulation_run=simulation_run,
            defaults={
                "company": simulation_run.scenario.company,
                "site": simulation_run.scenario.site,
                "result_status": result_status,
                "expected_result": expected_result,
                "actual_result": actual_result,
                "effectiveness_score": effectiveness_score,
                "effectiveness_level": effectiveness_level,
                "evaluation_summary": summary,
                "measured_at": timezone.now(),
            },
        )
        SystemEventService.log_system_event(
            event_type="optimization.outcome.measured",
            source_module="ai_optimization_loop",
            message="Simulation outcome measured.",
            entity_type="simulation",
            entity_id=str(simulation_run.public_id),
            company=simulation_run.scenario.company,
            site=simulation_run.scenario.site,
            payload={"effectiveness_score": str(effectiveness_score), "effectiveness_level": effectiveness_level},
        )
        return outcome


class CopilotFeedbackService:
    @classmethod
    def measure_message_quality(cls, *, message: ManagerCopilotMessage):
        feedback_average = _feedback_avg(FeedbackSignal.SourceType.COPILOT_MESSAGE, message.public_id)
        if feedback_average is None:
            return None
        effectiveness_score = EffectivenessScoringService.clamp(feedback_average)
        return {
            "message_public_id": str(message.public_id),
            "effectiveness_score": str(effectiveness_score),
            "effectiveness_level": EffectivenessScoringService.classify(effectiveness_score),
        }
