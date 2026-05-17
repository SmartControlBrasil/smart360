from __future__ import annotations

from apps.ai_experimentation_framework.models import Experiment

from .assignment import ExperimentAssignmentService
from .lifecycle import ExperimentLifecycleService
from .metrics import ExperimentMetricService


class ExperimentationEngine:
    @staticmethod
    def resolve_assignment(*, target_component, target_reference="", entity_key="", entity_type="", company=None, site=None, context=None):
        experiment = ExperimentAssignmentService.get_active_experiment(
            target_component=target_component,
            target_reference=target_reference,
            company=company,
            site=site,
        )
        if experiment is None:
            return None
        return ExperimentAssignmentService.assign(
            experiment=experiment,
            entity_key=entity_key,
            entity_type=entity_type,
            company=company,
            site=site,
            context=context,
        )

    @staticmethod
    def record_assignment_metric(*, assignment, metric_type, value, unit="", source_component="", source_reference="", metadata=None):
        if assignment is None:
            return None
        return ExperimentMetricService.record_metric(
            assignment=assignment,
            metric_type=metric_type,
            value=value,
            unit=unit,
            source_component=source_component,
            source_reference=source_reference,
            metadata=metadata,
        )

    create_experiment = ExperimentLifecycleService.create_experiment
    complete_experiment = ExperimentLifecycleService.complete_experiment
    promote_variant = ExperimentLifecycleService.promote_variant

