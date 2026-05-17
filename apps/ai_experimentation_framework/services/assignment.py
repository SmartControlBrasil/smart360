from __future__ import annotations

import hashlib

from django.db import transaction
from django.utils import timezone

from apps.ai_experimentation_framework.models import Experiment, ExperimentAssignment, Variant
from apps.ai_policy_studio.services.engine import PolicyStudioEngine

from .audit import ExperimentAuditService


class ExperimentAssignmentService:
    @staticmethod
    def _hash_ratio(*, experiment: Experiment, entity_key: str) -> int:
        digest = hashlib.md5(f"{experiment.public_id}:{entity_key}".encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % 10000

    @staticmethod
    def _match_rule_based_variant(*, experiment: Experiment, context: dict) -> Variant | None:
        rules = (experiment.configuration_payload or {}).get("assignment_rules", [])
        for rule in rules:
            conditions = rule.get("when", {})
            if all(context.get(key) == value for key, value in conditions.items()):
                slug = rule.get("variant_slug", "")
                return experiment.variants.filter(slug=slug, enabled=True).first()
        return None

    @classmethod
    def get_active_experiment(cls, *, target_component, target_reference="", company=None, site=None):
        queryset = Experiment.objects.select_related("company", "site", "winner_variant").prefetch_related("variants").filter(
            status=Experiment.Status.RUNNING,
            target_component=target_component,
        )
        if target_reference:
            queryset = queryset.filter(target_reference=target_reference)
        if company is not None:
            queryset = queryset.filter(company=company)
        else:
            queryset = queryset.filter(company__isnull=True)
        if site is not None:
            queryset = queryset.filter(site=site)
        return queryset.order_by("-start_date").first()

    @classmethod
    @transaction.atomic
    def assign(
        cls,
        *,
        experiment: Experiment,
        entity_key: str,
        entity_type="",
        company=None,
        site=None,
        context=None,
    ):
        context = context or {}
        assignment = ExperimentAssignment.objects.select_related("variant", "experiment").filter(
            experiment=experiment,
            entity_key=entity_key,
        ).first()
        if assignment is not None:
            return assignment

        policy_result = PolicyStudioEngine.evaluate(
            module_slug="ai_experimentation_framework",
            action_type="assign_variant",
            company=company or experiment.company,
            site=site or experiment.site,
            risk_level="low",
            autonomy_level=1,
            context={"target_component": experiment.target_component, "target_reference": experiment.target_reference},
        )
        if not policy_result.allowed:
            raise PermissionError(policy_result.reason)

        variants = list(experiment.variants.filter(enabled=True).order_by("id"))
        if not variants:
            raise ValueError("Experiment has no enabled variants.")
        variant = None
        reason = experiment.assignment_strategy
        if experiment.assignment_strategy == Experiment.AssignmentStrategy.RULE_BASED:
            variant = cls._match_rule_based_variant(experiment=experiment, context=context)
            reason = "rule_based"
        if variant is None:
            bucket = cls._hash_ratio(experiment=experiment, entity_key=entity_key)
            total_weight = sum(max(item.weight, 1) for item in variants)
            cursor = 0
            normalized = bucket % total_weight
            for item in variants:
                cursor += max(item.weight, 1)
                if normalized < cursor:
                    variant = item
                    break
        variant = variant or variants[0]
        assignment = ExperimentAssignment.objects.create(
            experiment=experiment,
            variant=variant,
            company=company or experiment.company,
            site=site or experiment.site,
            entity_key=entity_key,
            entity_type=entity_type,
            assignment_reason=reason,
            context_payload=context,
            assigned_at=timezone.now(),
        )
        ExperimentAuditService.log_event(
            experiment=experiment,
            variant=variant,
            event_type="variant.assigned",
            message=f"Variant {variant.slug} assigned to {entity_key}.",
            payload={"entity_key": entity_key, "entity_type": entity_type, "assignment_reason": reason},
        )
        return assignment

