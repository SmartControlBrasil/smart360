from decimal import Decimal

from django.db import transaction
from django.db.models import Avg
from django.utils import timezone

from apps.audit.services.audit_service import AuditService

from ..models import (
    AnalyticalAssignment,
    AnalyticalMatchingRecord,
    AnalyticalReview,
)


class AnalyticalMatchingService:
    @staticmethod
    def calculate_match_score(*, provider, analytical_request):
        score = Decimal("0.00")
        if provider.marketplace_status == provider.MarketplaceStatus.AVAILABLE:
            score += Decimal("30")
        if provider.verification_status == provider.VerificationStatus.APPROVED:
            score += Decimal("25")
        if provider.completed_jobs_count:
            score += min(Decimal(provider.completed_jobs_count), Decimal("20"))
        if provider.rating_average:
            score += Decimal(provider.rating_average) * Decimal("5")
        if provider.services.filter(category=analytical_request.category, is_active=True).exists():
            score += Decimal("20")
        return min(score, Decimal("100.00"))


class AnalyticalAssignmentService:
    @staticmethod
    @transaction.atomic
    def assign(*, analytical_request, provider, notes=""):
        assignment, created = AnalyticalAssignment.objects.get_or_create(
            analytical_request=analytical_request,
            provider=provider,
            defaults={"status": AnalyticalAssignment.Status.ASSIGNED, "notes": notes},
        )
        if not created and notes:
            assignment.notes = notes
            assignment.save(update_fields=["notes", "updated_at"])
        if created:
            analytical_request.status = analytical_request.Status.ASSIGNED
            analytical_request.save(update_fields=["status", "updated_at"])
            AnalyticalMatchingRecord.objects.update_or_create(
                analytical_request=analytical_request,
                provider=provider,
                defaults={
                    "match_score": AnalyticalMatchingService.calculate_match_score(
                        provider=provider,
                        analytical_request=analytical_request,
                    ),
                    "status": AnalyticalMatchingRecord.Status.ACCEPTED,
                },
            )
        return assignment

    @staticmethod
    def transition_status(*, assignment, status):
        assignment.status = status
        now = timezone.now()
        if status == AnalyticalAssignment.Status.ACCEPTED and not assignment.accepted_at:
            assignment.accepted_at = now
        if status == AnalyticalAssignment.Status.DECLINED and not assignment.declined_at:
            assignment.declined_at = now
        if status == AnalyticalAssignment.Status.IN_PROGRESS and not assignment.started_at:
            assignment.started_at = now
            assignment.analytical_request.status = assignment.analytical_request.Status.IN_PROGRESS
            assignment.analytical_request.save(update_fields=["status", "updated_at"])
        if status == AnalyticalAssignment.Status.COMPLETED and not assignment.completed_at:
            assignment.completed_at = now
            assignment.analytical_request.status = assignment.analytical_request.Status.DELIVERED
            assignment.analytical_request.save(update_fields=["status", "updated_at"])
            provider = assignment.provider
            provider.completed_jobs_count = provider.assignments.filter(status=AnalyticalAssignment.Status.COMPLETED).count()
            provider.save(update_fields=["completed_jobs_count", "updated_at"])
        assignment.save()
        return assignment


class AnalyticalReviewService:
    @staticmethod
    def refresh_rating(*, provider):
        aggregation = provider.reviews.aggregate(avg=Avg("rating"))
        provider.rating_average = aggregation["avg"] or 0
        provider.save(update_fields=["rating_average", "updated_at"])
        return provider

    @staticmethod
    def create_review(*, user, validated_data):
        review = AnalyticalReview.objects.create(**validated_data)
        AnalyticalReviewService.refresh_rating(provider=review.analytical_assignment.provider)
        AuditService.log(
            action="marketplace_analytical.review.created",
            entity="analytical_review",
            entity_id=str(review.public_id),
            user=user,
            company=review.reviewer_company,
            payload={"rating": review.rating},
        )
        return review
