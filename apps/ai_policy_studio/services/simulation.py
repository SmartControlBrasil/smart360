from django.db.models import Count

from apps.ai_decision_engine.models import AgentDecision
from apps.ai_policy_studio.models import PolicySimulationRun


class PolicySimulationService:
    @classmethod
    def simulate(cls, *, policy, company=None, site=None, created_by_user=None, input_payload=None):
        queryset = AgentDecision.objects.all()
        if company is not None:
            queryset = queryset.filter(company=company)
        if site is not None:
            queryset = queryset.filter(site=site)
        summary = queryset.values("decision_status").annotate(total=Count("id")).order_by("decision_status")
        result_payload = {
            "decision_status_distribution": list(summary),
            "would_affect_actions": queryset.count(),
            "risk_operational_index": queryset.filter(risk_level__in=["high", "critical"]).count(),
            "auto_executed_count": queryset.filter(decision_status="executed", requires_human_approval=False).count(),
        }
        return PolicySimulationRun.objects.create(
            policy=policy,
            company=company,
            site=site,
            created_by_user=created_by_user,
            input_payload=input_payload or {},
            result_payload=result_payload,
        )

