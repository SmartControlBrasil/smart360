from decimal import Decimal

from apps.ai_experimentation_framework.models import ExperimentAssignment, ExperimentMetric
from apps.ai_policy_studio.services.engine import PolicyStudioEngine

from .audit import ExperimentAuditService


class ExperimentMetricService:
    @classmethod
    def record_metric(
        cls,
        *,
        assignment: ExperimentAssignment,
        metric_type: str,
        value,
        unit="",
        source_component="",
        source_reference="",
        metadata=None,
    ):
        metadata = metadata or {}
        policy_result = PolicyStudioEngine.evaluate(
            module_slug="ai_experimentation_framework",
            action_type="record_metric",
            company=assignment.company or assignment.experiment.company,
            site=assignment.site or assignment.experiment.site,
            risk_level="low",
            autonomy_level=1,
            context={"metric_type": metric_type, "target_component": assignment.experiment.target_component},
        )
        if not policy_result.allowed:
            raise PermissionError(policy_result.reason)
        metric = ExperimentMetric.objects.create(
            experiment=assignment.experiment,
            variant=assignment.variant,
            assignment=assignment,
            company=assignment.company,
            site=assignment.site,
            metric_type=metric_type,
            value=Decimal(str(value)),
            unit=unit,
            source_component=source_component,
            source_reference=source_reference,
            metadata=metadata,
        )
        ExperimentAuditService.log_event(
            experiment=assignment.experiment,
            variant=assignment.variant,
            event_type="metric.recorded",
            message=f"Metric {metric_type} recorded for variant {assignment.variant.slug}.",
            payload={"metric_type": metric_type, "value": str(metric.value), "source_reference": source_reference},
        )
        return metric

