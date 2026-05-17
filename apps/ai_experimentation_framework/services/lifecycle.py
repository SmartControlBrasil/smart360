from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.ai_experimentation_framework.models import Experiment, Variant
from apps.ai_optimization_loop.models import OptimizationPolicy, OptimizationProposal
from apps.ai_policy_studio.services.engine import PolicyStudioEngine

from .analysis import ExperimentAnalysisService
from .audit import ExperimentAuditService


class ExperimentLifecycleService:
    @classmethod
    @transaction.atomic
    def create_experiment(
        cls,
        *,
        name,
        description,
        target_component,
        target_reference="",
        company=None,
        site=None,
        created_by_user=None,
        variants=None,
        assignment_strategy=Experiment.AssignmentStrategy.WEIGHTED,
        primary_metric="effectiveness_score",
        success_direction=Experiment.SuccessDirection.HIGHER_IS_BETTER,
        min_sample_size=20,
        min_runtime_hours=24,
        auto_promote=False,
        configuration_payload=None,
    ):
        policy_result = PolicyStudioEngine.evaluate(
            module_slug="ai_experimentation_framework",
            action_type="create_experiment",
            company=company,
            site=site,
            risk_level="medium",
            autonomy_level=1,
            context={"target_component": target_component, "target_reference": target_reference},
        )
        if not policy_result.allowed:
            raise PermissionError(policy_result.reason)
        experiment = Experiment.objects.create(
            company=company,
            site=site,
            name=name,
            slug=slugify(f"{target_component}-{target_reference or name}-{timezone.now().strftime('%Y%m%d%H%M%S')}")[:180],
            description=description,
            target_component=target_component,
            target_reference=target_reference,
            status=Experiment.Status.RUNNING,
            start_date=timezone.now(),
            assignment_strategy=assignment_strategy,
            primary_metric=primary_metric,
            success_direction=success_direction,
            min_sample_size=min_sample_size,
            min_runtime_hours=min_runtime_hours,
            auto_promote=auto_promote,
            configuration_payload=configuration_payload or {},
            created_by_user=created_by_user,
        )
        variants = variants or [
            {"name": "Variant A", "slug": "variant-a", "weight": 50, "is_control": True, "config_payload": {}},
            {"name": "Variant B", "slug": "variant-b", "weight": 50, "is_control": False, "config_payload": {}},
        ]
        traffic_split = {}
        for item in variants:
            variant = Variant.objects.create(
                experiment=experiment,
                name=item["name"],
                slug=item["slug"],
                description=item.get("description", ""),
                config_payload=item.get("config_payload", {}),
                weight=item.get("weight", 50),
                enabled=item.get("enabled", True),
                is_control=item.get("is_control", False),
            )
            traffic_split[variant.slug] = variant.weight
        experiment.traffic_split = traffic_split
        experiment.save(update_fields=["traffic_split", "updated_at"])
        ExperimentAuditService.log_event(
            experiment=experiment,
            event_type="experiment.created",
            actor_user=created_by_user,
            message=f"Experiment {experiment.slug} created.",
            payload={"target_component": target_component, "target_reference": target_reference, "traffic_split": traffic_split},
        )
        return experiment

    @classmethod
    @transaction.atomic
    def complete_experiment(cls, *, experiment: Experiment, actor_user=None):
        policy_result = PolicyStudioEngine.evaluate(
            module_slug="ai_experimentation_framework",
            action_type="complete_experiment",
            company=experiment.company,
            site=experiment.site,
            risk_level="medium",
            autonomy_level=1,
            context={"target_component": experiment.target_component, "target_reference": experiment.target_reference},
        )
        if not policy_result.allowed:
            raise PermissionError(policy_result.reason)
        result = ExperimentAnalysisService.analyze(experiment=experiment)
        experiment.status = Experiment.Status.COMPLETED
        experiment.end_date = timezone.now()
        experiment.winner_variant = result.winning_variant
        experiment.save(update_fields=["status", "end_date", "winner_variant", "updated_at"])
        if experiment.auto_promote and result.winning_variant is not None and result.confidence_level != "low":
            cls.promote_variant(experiment=experiment, variant=result.winning_variant, actor_user=actor_user, auto=True)
        return experiment

    @classmethod
    @transaction.atomic
    def promote_variant(cls, *, experiment: Experiment, variant: Variant, actor_user=None, auto=False):
        policy_result = PolicyStudioEngine.evaluate(
            module_slug="ai_experimentation_framework",
            action_type="promote_variant",
            company=experiment.company,
            site=experiment.site,
            risk_level="high",
            autonomy_level=2 if auto else 1,
            context={
                "target_component": experiment.target_component,
                "target_reference": experiment.target_reference,
                "auto": auto,
            },
        )
        if not policy_result.allowed:
            raise PermissionError(policy_result.reason)
        if policy_result.requires_approval and auto:
            raise PermissionError(policy_result.reason)
        experiment.status = Experiment.Status.PROMOTED
        experiment.winner_variant = variant
        experiment.end_date = experiment.end_date or timezone.now()
        experiment.save(update_fields=["status", "winner_variant", "end_date", "updated_at"])
        ExperimentAuditService.log_event(
            experiment=experiment,
            variant=variant,
            actor_user=actor_user,
            event_type="variant.promoted",
            message=f"Variant {variant.slug} promoted for {experiment.target_component}.",
            payload={"target_reference": experiment.target_reference, "config_payload": variant.config_payload, "auto": auto},
        )
        cls._create_optimization_proposal(experiment=experiment, variant=variant)
        return experiment

    @staticmethod
    def _create_optimization_proposal(*, experiment: Experiment, variant: Variant):
        target_map = {
            Experiment.TargetComponent.AGENT: OptimizationPolicy.TargetType.AGENT_EXECUTION_POLICY,
            Experiment.TargetComponent.COPILOT: OptimizationPolicy.TargetType.COPILOT_CONFIGURATION,
            Experiment.TargetComponent.DECISION_ENGINE: OptimizationPolicy.TargetType.DECISION_POLICY,
            Experiment.TargetComponent.SIMULATION_ENGINE: OptimizationPolicy.TargetType.SIMULATION_TYPE,
            Experiment.TargetComponent.POLICY: OptimizationPolicy.TargetType.DECISION_POLICY,
            Experiment.TargetComponent.HEURISTIC: OptimizationPolicy.TargetType.SIMULATION_TYPE,
        }
        target_type = target_map.get(experiment.target_component, OptimizationPolicy.TargetType.COPILOT_CONFIGURATION)
        OptimizationProposal.objects.get_or_create(
            target_type=target_type,
            target_reference=experiment.target_reference or experiment.slug,
            proposal_type=OptimizationPolicy.ProposalType.HEURISTIC_CONFIG_ADJUSTMENT,
            source_outcome_type="experiment_result",
            source_outcome_reference=str(experiment.public_id),
            defaults={
                "company": experiment.company,
                "site": experiment.site,
                "current_value": {"active_strategy": "current"},
                "proposed_value": variant.config_payload,
                "rationale": f"Variant {variant.slug} venceu o experimento {experiment.slug}.",
                "evidence_summary": (experiment.result.summary if hasattr(experiment, "result") else ""),
                "expected_impact_summary": f"Promover estrategia vencedora para {experiment.target_component}:{experiment.target_reference}.",
                "risk_level": OptimizationPolicy.RiskLevel.MEDIUM,
                "status": OptimizationProposal.Status.PENDING_REVIEW,
                "metadata": {
                    "experiment_public_id": str(experiment.public_id),
                    "variant_public_id": str(variant.public_id),
                },
            },
        )

