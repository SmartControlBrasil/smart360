from decimal import Decimal

from django.db.models import Avg, Count, Q

from apps.ai_agents_center.models import AgentDefinition, ManagerCopilotMessage
from apps.ai_optimization_loop.models import DecisionOutcome, FeedbackSignal, OptimizationProposal, RecommendationOutcome, SimulationOutcome


class OptimizationQualityService:
    @classmethod
    def agent_quality(cls, *, company=None):
        agents = AgentDefinition.objects.filter(enabled=True).order_by("name")
        rows = []
        for agent in agents:
            runs = agent.runs.all()
            recommendations = RecommendationOutcome.objects.filter(recommendation__agent_run__agent=agent)
            decisions = DecisionOutcome.objects.filter(decision__agent_action_proposal__agent_run__agent=agent)
            if company is not None:
                runs = runs.filter(company=company)
                recommendations = recommendations.filter(company=company)
                decisions = decisions.filter(company=company)
            recommendation_avg = recommendations.aggregate(avg=Avg("effectiveness_score"))["avg"] or Decimal("0.00")
            decision_avg = decisions.aggregate(avg=Avg("effectiveness_score"))["avg"] or Decimal("0.00")
            rows.append(
                {
                    "agent_slug": agent.slug,
                    "agent_name": agent.name,
                    "runs_count": runs.count(),
                    "recommendations_count": recommendations.count(),
                    "decisions_count": decisions.count(),
                    "rejected_decisions": decisions.filter(result_status=DecisionOutcome.ResultStatus.FAILED).count(),
                    "recommendation_effectiveness": recommendation_avg,
                    "decision_effectiveness": decision_avg,
                    "composite_score": ((recommendation_avg or Decimal("0.00")) + (decision_avg or Decimal("0.00"))) / Decimal("2.00"),
                }
            )
        return sorted(rows, key=lambda item: item["composite_score"], reverse=True)

    @classmethod
    def copilot_quality(cls, *, company=None):
        queryset = ManagerCopilotMessage.objects.filter(role=ManagerCopilotMessage.Role.ASSISTANT)
        if company is not None:
            queryset = queryset.filter(session__company=company)
        rows = []
        for message in queryset.order_by("-created_at")[:50]:
            feedback_queryset = FeedbackSignal.objects.filter(
                source_type=FeedbackSignal.SourceType.COPILOT_MESSAGE,
                source_reference=str(message.public_id),
            )
            avg_feedback = feedback_queryset.aggregate(avg=Avg("score"))["avg"] or Decimal("0.00")
            rows.append(
                {
                    "message_public_id": str(message.public_id),
                    "session_public_id": str(message.session.public_id),
                    "detected_intent": message.detected_intent,
                    "score": avg_feedback,
                    "summary": message.content[:180],
                }
            )
        return rows

    @classmethod
    def overview(cls, *, company=None, site=None):
        recommendation_outcomes = RecommendationOutcome.objects.all()
        decision_outcomes = DecisionOutcome.objects.all()
        simulation_outcomes = SimulationOutcome.objects.all()
        proposals = OptimizationProposal.objects.all()
        feedbacks = FeedbackSignal.objects.all()
        if company is not None:
            recommendation_outcomes = recommendation_outcomes.filter(company=company)
            decision_outcomes = decision_outcomes.filter(company=company)
            simulation_outcomes = simulation_outcomes.filter(company=company)
            proposals = proposals.filter(Q(company=company) | Q(company__isnull=True))
            feedbacks = feedbacks.filter(Q(company=company) | Q(company__isnull=True))
        if site is not None:
            recommendation_outcomes = recommendation_outcomes.filter(site=site)
            decision_outcomes = decision_outcomes.filter(site=site)
            simulation_outcomes = simulation_outcomes.filter(site=site)
            proposals = proposals.filter(Q(site=site) | Q(site__isnull=True))
            feedbacks = feedbacks.filter(Q(site=site) | Q(site__isnull=True))
        return {
            "recommendation_avg": recommendation_outcomes.aggregate(avg=Avg("effectiveness_score"))["avg"] or Decimal("0.00"),
            "decision_avg": decision_outcomes.aggregate(avg=Avg("effectiveness_score"))["avg"] or Decimal("0.00"),
            "simulation_avg": simulation_outcomes.aggregate(avg=Avg("effectiveness_score"))["avg"] or Decimal("0.00"),
            "feedback_count": feedbacks.count(),
            "pending_proposals": proposals.filter(status=OptimizationProposal.Status.PENDING_REVIEW).count(),
            "applied_proposals": proposals.filter(status=OptimizationProposal.Status.APPLIED).count(),
        }

