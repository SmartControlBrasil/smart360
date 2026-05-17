from __future__ import annotations

from decimal import Decimal

from django.db.models import Avg, Count
from django.utils import timezone

from apps.ai_experimentation_framework.models import Experiment, ExperimentMetric, ExperimentResult

from .audit import ExperimentAuditService


class ExperimentAnalysisService:
    @staticmethod
    def _confidence_for_samples(sample_size: int) -> str:
        if sample_size >= 100:
            return ExperimentResult.ConfidenceLevel.HIGH
        if sample_size >= 30:
            return ExperimentResult.ConfidenceLevel.MEDIUM
        return ExperimentResult.ConfidenceLevel.LOW

    @classmethod
    def analyze(cls, *, experiment: Experiment):
        metrics = ExperimentMetric.objects.filter(experiment=experiment, metric_type=experiment.primary_metric)
        per_variant = []
        for variant in experiment.variants.filter(enabled=True).order_by("name"):
            row = metrics.filter(variant=variant).aggregate(sample_size=Count("id"), avg_value=Avg("value"))
            per_variant.append(
                {
                    "variant_public_id": str(variant.public_id),
                    "variant_slug": variant.slug,
                    "variant_name": variant.name,
                    "sample_size": row["sample_size"] or 0,
                    "avg_value": float(row["avg_value"] or 0),
                    "is_control": variant.is_control,
                    "config_payload": variant.config_payload,
                }
            )

        control = next((item for item in per_variant if item["is_control"]), per_variant[0] if per_variant else None)
        winner = None
        eligible_rows = [item for item in per_variant if item["sample_size"] >= experiment.min_sample_size]
        if eligible_rows:
            reverse = experiment.success_direction == Experiment.SuccessDirection.HIGHER_IS_BETTER
            winner = sorted(eligible_rows, key=lambda item: item["avg_value"], reverse=reverse)[0]

        for item in per_variant:
            baseline = control["avg_value"] if control else 0
            if baseline:
                item["delta_vs_control_pct"] = round(((item["avg_value"] - baseline) / baseline) * 100, 2)
            else:
                item["delta_vs_control_pct"] = 0.0

        sample_size = sum(item["sample_size"] for item in per_variant)
        confidence = cls._confidence_for_samples(sample_size)
        summary = (
            f"Experimento analisado com {sample_size} metricas na metrica principal {experiment.primary_metric}. "
            f"Vencedor atual: {winner['variant_name'] if winner else 'indefinido'}."
        )
        result_payload = {
            "evaluated_at": timezone.now().isoformat(),
            "primary_metric": experiment.primary_metric,
            "success_direction": experiment.success_direction,
            "variants": per_variant,
            "winner": winner or {},
            "min_sample_size": experiment.min_sample_size,
            "control_variant": control or {},
        }
        result, _ = ExperimentResult.objects.update_or_create(
            experiment=experiment,
            defaults={
                "winning_variant": experiment.variants.filter(public_id=winner["variant_public_id"]).first() if winner else None,
                "summary": summary,
                "primary_metric": experiment.primary_metric,
                "confidence_level": confidence,
                "result_payload": result_payload,
                "recommendation": cls._build_recommendation(experiment=experiment, winner=winner, confidence=confidence),
            },
        )
        ExperimentAuditService.log_event(
            experiment=experiment,
            variant=result.winning_variant,
            event_type="experiment.completed",
            message=summary,
            payload={"confidence_level": confidence, "winner_variant": winner["variant_slug"] if winner else ""},
        )
        return result

    @staticmethod
    def _build_recommendation(*, experiment: Experiment, winner: dict | None, confidence: str) -> str:
        if not winner:
            return "Continuar coletando metricas antes de promover qualquer variante."
        if confidence == ExperimentResult.ConfidenceLevel.LOW:
            return f"Variante {winner['variant_slug']} lidera, mas a confianca ainda e baixa."
        return f"Variante {winner['variant_slug']} lidera na metrica {experiment.primary_metric} e pode ser considerada para promocao."

