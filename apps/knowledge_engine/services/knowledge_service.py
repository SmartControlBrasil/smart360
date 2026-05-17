from django.db.models import Avg

from apps.audit.services.audit_service import AuditService

from ..models import KnowledgeFeedback


class KnowledgeFeedbackService:
    @staticmethod
    def create_feedback(*, user, validated_data):
        feedback = KnowledgeFeedback.objects.create(**validated_data)
        AuditService.log(
            action="knowledge_engine.feedback.created",
            entity="knowledge_feedback",
            entity_id=str(feedback.public_id),
            user=user,
            payload={
                "item_type": feedback.item_type,
                "item_id": feedback.item_id,
                "usefulness_rating": feedback.usefulness_rating,
            },
        )
        return feedback


class KnowledgeInsightService:
    @staticmethod
    def average_usefulness_for_item(*, item_type, item_id):
        result = KnowledgeFeedback.objects.filter(item_type=item_type, item_id=item_id).aggregate(avg=Avg("usefulness_rating"))
        return result["avg"] or 0
