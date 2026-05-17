from django.db.models import Avg

from apps.ai_optimization_loop.models import FeedbackSignal
from apps.observability_center.services.observability_service import SystemEventService


class FeedbackSignalService:
    @classmethod
    def register(
        cls,
        *,
        source_type,
        source_reference,
        signal_type,
        score,
        company=None,
        site=None,
        user=None,
        comment="",
        metadata=None,
    ):
        feedback = FeedbackSignal.objects.create(
            source_type=source_type,
            source_reference=str(source_reference),
            company=company,
            site=site,
            user=user,
            signal_type=signal_type,
            score=score,
            comment=comment,
            metadata=metadata or {},
        )
        SystemEventService.log_system_event(
            event_type="optimization.feedback.received",
            source_module="ai_optimization_loop",
            message="Optimization feedback received.",
            entity_type=source_type,
            entity_id=str(source_reference),
            user=user,
            company=company,
            site=site,
            payload={"signal_type": signal_type, "score": str(score)},
        )
        return feedback

    @staticmethod
    def average_score(*, source_type, source_reference):
        result = FeedbackSignal.objects.filter(
            source_type=source_type,
            source_reference=str(source_reference),
        ).aggregate(avg=Avg("score"))
        return result["avg"]

