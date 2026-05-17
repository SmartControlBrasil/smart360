from apps.ai_optimization_loop.models import OptimizationPolicy


class OptimizationPolicyService:
    @classmethod
    def resolve_policy(cls, *, target_type, proposal_type, risk_level):
        queryset = OptimizationPolicy.objects.filter(
            target_type=target_type,
            proposal_type=proposal_type,
            enabled=True,
        ).order_by("created_at")
        policy = queryset.filter(risk_level=risk_level).first() or queryset.first()
        return policy

