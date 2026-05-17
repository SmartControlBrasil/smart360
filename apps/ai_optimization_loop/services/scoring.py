from decimal import Decimal

from apps.ai_optimization_loop.models import EffectivenessLevel


class EffectivenessScoringService:
    @staticmethod
    def clamp(score) -> Decimal:
        value = Decimal(str(score or 0))
        if value < Decimal("0"):
            return Decimal("0.00")
        if value > Decimal("100"):
            return Decimal("100.00")
        return value.quantize(Decimal("0.01"))

    @classmethod
    def classify(cls, score) -> str:
        value = cls.clamp(score)
        if value >= Decimal("80"):
            return EffectivenessLevel.VERY_EFFECTIVE
        if value >= Decimal("60"):
            return EffectivenessLevel.EFFECTIVE
        if value >= Decimal("45"):
            return EffectivenessLevel.NEUTRAL
        if value >= Decimal("25"):
            return EffectivenessLevel.WEAK
        return EffectivenessLevel.HARMFUL

    @classmethod
    def apply_feedback_adjustment(cls, *, base_score, feedback_average=None):
        base = cls.clamp(base_score)
        if feedback_average is None:
            return base
        feedback = cls.clamp(feedback_average)
        adjustment = (feedback - Decimal("50.00")) / Decimal("2.00")
        return cls.clamp(base + adjustment)

