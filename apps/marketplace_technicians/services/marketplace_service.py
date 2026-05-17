from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.audit.services.audit_service import AuditService
from apps.ai_shared.interfaces.triggers import (
    get_anomaly_agent_trigger_service,
    get_marketplace_allocation_trigger_service,
    get_scheduling_agent_trigger_service,
)
from apps.smart_system.models import ServiceOrder
from apps.smart_system.services.maintenance_service import ServiceOrderService

from ..models import (
    TechnicianAssignment,
    TechnicianCompensationRecord,
    TechnicianMatchingRecord,
    TechnicianReview,
    TechnicianServiceOffer,
    TechnicianServiceRequest,
    TechnicianWorkReport,
)


class TechnicianMatchingService:
    WEIGHTS = {
        "specialty": Decimal("0.30"),
        "distance": Decimal("0.25"),
        "rating": Decimal("0.20"),
        "experience": Decimal("0.15"),
        "availability": Decimal("0.10"),
    }
    SCORING_VERSION = "v1"

    @staticmethod
    def _normalize_score(value):
        value = max(Decimal("0"), min(Decimal("1"), Decimal(str(value))))
        return (value * Decimal("100")).quantize(Decimal("0.01"))

    @staticmethod
    def _normalized_rating(technician_profile):
        rating = Decimal(str(technician_profile.rating_average or 0))
        return min(rating / Decimal("5"), Decimal("1"))

    @staticmethod
    def _specialty_factor(*, technician_profile, service_request):
        if not service_request.category:
            return Decimal("0.35")
        category = service_request.category.lower().strip()
        skill_names = [
            name.lower()
            for name in technician_profile.skill_assignments.select_related("skill").values_list("skill__name", flat=True)
        ]
        if not skill_names:
            return Decimal("0")
        if any(category == skill for skill in skill_names):
            return Decimal("1")
        if any(category in skill or skill in category for skill in skill_names):
            return Decimal("0.82")
        keyword_groups = {
            "ar condicionado": ["hvac", "climatizacao", "refrigeracao"],
            "hvac": ["ar condicionado", "climatizacao"],
            "camaras climaticas": ["climatizacao", "refrigeracao", "hvac"],
            "automacao industrial": ["automacao", "paineis eletricos", "inversores de frequencia"],
            "esteiras de academia": ["academia", "motores", "painel eletrico"],
            "inversores de frequencia": ["inversores", "automacao industrial", "paineis eletricos"],
            "painéis elétricos": ["paineis eletricos", "automacao industrial", "inversores de frequencia"],
            "painéis eletricos": ["paineis eletricos", "automacao industrial", "inversores de frequencia"],
        }
        related_keywords = keyword_groups.get(category, [])
        if related_keywords and any(
            any(keyword in skill for keyword in related_keywords)
            for skill in skill_names
        ):
            return Decimal("0.65")
        return Decimal("0.15")

    @staticmethod
    def _distance_factor(*, technician_profile, service_request):
        profile_regions = technician_profile.service_regions.select_related("service_region")
        if not profile_regions.exists():
            return Decimal("0.10"), None
        state_match = profile_regions.filter(service_region__state__iexact=service_request.state)
        if not state_match.exists():
            return Decimal("0"), None
        if service_request.city:
            city_match = state_match.filter(service_region__city__iexact=service_request.city)
            if city_match.exists():
                return Decimal("1"), Decimal("5.00")
            broad_state = state_match.filter(Q(service_region__city="") | Q(service_region__city__isnull=True))
            if broad_state.exists():
                return Decimal("0.72"), Decimal(str(max(technician_profile.service_radius_km * 0.6, 15)))
            return Decimal("0.45"), Decimal(str(max(technician_profile.service_radius_km * 0.9, 30)))
        return Decimal("0.55"), Decimal(str(max(technician_profile.service_radius_km, 30)))

    @staticmethod
    def _experience_factor(*, technician_profile, service_request):
        completed_assignments = technician_profile.assignments.filter(
            assignment_status=TechnicianAssignment.AssignmentStatus.COMPLETED
        )
        completed_count = completed_assignments.count()
        volume_factor = min(Decimal(completed_count) / Decimal("20"), Decimal("1")) if completed_count else Decimal("0")
        category_factor = Decimal("0")
        asset_factor = Decimal("0")
        if service_request.category:
            category_factor = Decimal("1") if completed_assignments.filter(
                technician_service_request__category__iexact=service_request.category
            ).exists() else Decimal("0")
        if service_request.related_asset_id:
            asset_factor = Decimal("1") if completed_assignments.filter(
                technician_service_request__related_asset_id=service_request.related_asset_id
            ).exists() else Decimal("0")
        elif service_request.related_asset and service_request.related_asset.category_id:
            asset_factor = Decimal("1") if completed_assignments.filter(
                technician_service_request__related_asset__category_id=service_request.related_asset.category_id
            ).exists() else Decimal("0")
        years_factor = min(Decimal(technician_profile.experience_years or 0) / Decimal("10"), Decimal("1"))
        return max(category_factor, asset_factor, (volume_factor * Decimal("0.5")) + (years_factor * Decimal("0.5")))

    @staticmethod
    def _availability_factor(*, technician_profile):
        active_assignments = technician_profile.assignments.filter(
            assignment_status__in=[
                TechnicianAssignment.AssignmentStatus.ASSIGNED,
                TechnicianAssignment.AssignmentStatus.ACCEPTED,
                TechnicianAssignment.AssignmentStatus.IN_PROGRESS,
            ]
        ).count()
        if technician_profile.marketplace_status == technician_profile.MarketplaceStatus.AVAILABLE:
            base = Decimal("1")
        elif technician_profile.marketplace_status == technician_profile.MarketplaceStatus.BUSY:
            base = Decimal("0.45")
        else:
            base = Decimal("0")
        if technician_profile.availabilities.filter(is_available=True).exists():
            base += Decimal("0.10")
        load_penalty = min(Decimal(active_assignments) * Decimal("0.12"), Decimal("0.60"))
        return max(Decimal("0"), min(base - load_penalty, Decimal("1")))

    @staticmethod
    def _response_time_factor(*, technician_profile):
        average_response = technician_profile.offers.aggregate(avg_response=Avg("estimated_hours"))["avg_response"]
        if average_response is None:
            return Decimal("0.50")
        average_response = Decimal(str(average_response))
        if average_response <= Decimal("2"):
            return Decimal("1")
        if average_response <= Decimal("6"):
            return Decimal("0.80")
        if average_response <= Decimal("12"):
            return Decimal("0.60")
        return Decimal("0.30")

    @classmethod
    def calculate_match_breakdown(cls, *, technician_profile, service_request):
        specialty_factor = cls._specialty_factor(
            technician_profile=technician_profile,
            service_request=service_request,
        )
        distance_factor, distance_km = cls._distance_factor(
            technician_profile=technician_profile,
            service_request=service_request,
        )
        rating_factor = cls._normalized_rating(technician_profile)
        experience_factor = cls._experience_factor(
            technician_profile=technician_profile,
            service_request=service_request,
        )
        availability_factor = cls._availability_factor(technician_profile=technician_profile)
        response_time_factor = cls._response_time_factor(technician_profile=technician_profile)
        total_factor = (
            (specialty_factor * cls.WEIGHTS["specialty"])
            + (distance_factor * cls.WEIGHTS["distance"])
            + (rating_factor * cls.WEIGHTS["rating"])
            + (experience_factor * cls.WEIGHTS["experience"])
            + (availability_factor * cls.WEIGHTS["availability"])
        )
        return {
            "score_total": cls._normalize_score(total_factor),
            "score_specialty": cls._normalize_score(specialty_factor),
            "score_distance": cls._normalize_score(distance_factor),
            "score_rating": cls._normalize_score(rating_factor),
            "score_experience": cls._normalize_score(experience_factor),
            "score_availability": cls._normalize_score(availability_factor),
            "score_response_time": cls._normalize_score(response_time_factor),
            "distance_km": distance_km,
            "calculation_context": {
                "weights": {key: str(value) for key, value in cls.WEIGHTS.items()},
                "specialty_factor": str(specialty_factor),
                "distance_factor": str(distance_factor),
                "rating_factor": str(rating_factor),
                "experience_factor": str(experience_factor),
                "availability_factor": str(availability_factor),
                "response_time_factor": str(response_time_factor),
            },
        }

    @staticmethod
    def calculate_match_score(*, technician_profile, service_request):
        return TechnicianMatchingService.calculate_match_breakdown(
            technician_profile=technician_profile,
            service_request=service_request,
        )["score_total"]

    @staticmethod
    def build_match_reason(*, technician_profile, service_request):
        reasons = []
        breakdown = TechnicianMatchingService.calculate_match_breakdown(
            technician_profile=technician_profile,
            service_request=service_request,
        )
        if breakdown["score_specialty"] >= Decimal("65"):
            reasons.append("especialidade aderente")
        if breakdown["score_distance"] >= Decimal("45") and technician_profile.service_regions.filter(
            service_region__state__iexact=service_request.state
        ).exists():
            reasons.append("regiao atendida")
        if technician_profile.marketplace_status == technician_profile.MarketplaceStatus.AVAILABLE:
            reasons.append("disponivel")
        if technician_profile.verification_status == technician_profile.VerificationStatus.APPROVED:
            reasons.append("perfil verificado")
        if breakdown["score_experience"] >= Decimal("60"):
            reasons.append("experiencia similar")
        if breakdown["score_rating"] >= Decimal("80"):
            reasons.append("boa reputacao")
        return ", ".join(reasons) or "compatibilidade basica de regiao e disponibilidade"

    @staticmethod
    def refresh_matches(*, service_request):
        from ..models import TechnicianProfile

        candidates = TechnicianProfile.objects.filter(
            is_active=True,
            marketplace_status__in=[
                TechnicianProfile.MarketplaceStatus.AVAILABLE,
                TechnicianProfile.MarketplaceStatus.BUSY,
            ],
        )
        candidate_ids = list(candidates.values_list("id", flat=True)[:50])
        service_request.matching_records.exclude(technician_profile_id__in=candidate_ids).delete()
        scored_records = []
        for technician_profile in candidates.filter(id__in=candidate_ids):
            record, _ = TechnicianMatchingRecord.objects.update_or_create(
                technician_service_request=service_request,
                technician_profile=technician_profile,
                defaults=TechnicianMatchingService.build_record_defaults(
                    technician_profile=technician_profile,
                    service_request=service_request,
                    status=TechnicianMatchingRecord.Status.SUGGESTED,
                ),
            )
            scored_records.append(record)
        for position, record in enumerate(
            sorted(scored_records, key=lambda item: (item.match_score or Decimal("0"), item.score_rating), reverse=True),
            start=1,
        ):
            if record.ranking_position != position:
                record.ranking_position = position
                record.save(update_fields=["ranking_position", "updated_at"])
        if service_request.matching_records.exists():
            service_request.status = TechnicianServiceRequest.Status.MATCHING
            service_request.save(update_fields=["status", "updated_at"])
        return service_request

    @staticmethod
    def get_ranked_matches(*, service_request, limit=10):
        return service_request.matching_records.select_related(
            "technician_profile",
            "technician_profile__user",
        ).order_by("ranking_position", "-match_score", "-score_rating")[:limit]

    @staticmethod
    def build_record_defaults(*, technician_profile, service_request, status):
        breakdown = TechnicianMatchingService.calculate_match_breakdown(
            technician_profile=technician_profile,
            service_request=service_request,
        )
        return {
            "match_score": breakdown["score_total"],
            "score_specialty": breakdown["score_specialty"],
            "score_distance": breakdown["score_distance"],
            "score_rating": breakdown["score_rating"],
            "score_experience": breakdown["score_experience"],
            "score_availability": breakdown["score_availability"],
            "score_response_time": breakdown["score_response_time"],
            "distance_km": breakdown["distance_km"],
            "scoring_version": TechnicianMatchingService.SCORING_VERSION,
            "calculation_context": breakdown["calculation_context"],
            "match_reason": TechnicianMatchingService.build_match_reason(
                technician_profile=technician_profile,
                service_request=service_request,
            ),
            "status": status,
        }


class TechnicianServiceRequestService:
    @staticmethod
    @transaction.atomic
    def create_request(*, user, validated_data):
        related_site = validated_data.get("related_site")
        related_client = validated_data.get("related_client") or getattr(related_site, "maintenance_client", None)
        requester_company = validated_data.get("requester_company") or getattr(related_client, "company", None)
        validated_data["requester_user"] = validated_data.get("requester_user") or user
        validated_data["requester_company"] = requester_company
        if related_client is not None:
            validated_data["related_client"] = related_client
        service_request = TechnicianServiceRequest.objects.create(**validated_data)
        TechnicianMatchingService.refresh_matches(service_request=service_request)
        AuditService.log(
            action="marketplace_technicians.request.created",
            entity="technician_service_request",
            entity_id=str(service_request.public_id),
            user=user,
            company=service_request.requester_company,
            payload={"status": service_request.status, "service_type": service_request.service_type},
        )
        try:
            marketplace_trigger_service = get_marketplace_allocation_trigger_service()
            marketplace_trigger_service.run_for_request(service_request=service_request, user=user)
        except Exception:
            pass
        try:
            anomaly_trigger_service = get_anomaly_agent_trigger_service()
            anomaly_trigger_service.trigger_for_marketplace_request(service_request=service_request, user=user)
        except Exception:
            pass
        return service_request


class TechnicianServiceOfferService:
    @staticmethod
    @transaction.atomic
    def create_offer(*, user, validated_data):
        service_request = validated_data["service_request"]
        technician_profile = validated_data["technician_profile"]
        offer = TechnicianServiceOffer.objects.create(**validated_data)
        service_request.status = TechnicianServiceRequest.Status.OFFERS_RECEIVED
        service_request.save(update_fields=["status", "updated_at"])
        TechnicianMatchingRecord.objects.update_or_create(
            technician_service_request=service_request,
            technician_profile=technician_profile,
            defaults=TechnicianMatchingService.build_record_defaults(
                technician_profile=technician_profile,
                service_request=service_request,
                status=TechnicianMatchingRecord.Status.NOTIFIED,
            ),
        )
        AuditService.log(
            action="marketplace_technicians.offer.created",
            entity="technician_service_offer",
            entity_id=str(offer.public_id),
            user=user,
            company=service_request.requester_company,
            payload={"status": offer.status, "proposed_amount": str(offer.proposed_amount)},
        )
        try:
            marketplace_trigger_service = get_marketplace_allocation_trigger_service()
            marketplace_trigger_service.run_for_offer(offer=offer, user=user)
        except Exception:
            pass
        try:
            anomaly_trigger_service = get_anomaly_agent_trigger_service()
            anomaly_trigger_service.trigger_for_marketplace_request(service_request=service_request, user=user)
        except Exception:
            pass
        return offer

    @staticmethod
    @transaction.atomic
    def accept_offer(*, user, offer):
        offer.status = TechnicianServiceOffer.Status.ACCEPTED
        offer.save(update_fields=["status", "updated_at"])
        offer.service_request.offers.exclude(pk=offer.pk).update(status=TechnicianServiceOffer.Status.REJECTED)
        assignment = TechnicianAssignmentService.assign(
            service_request=offer.service_request,
            technician_profile=offer.technician_profile,
            service_offer=offer,
            notes=offer.message,
        )
        AuditService.log(
            action="marketplace_technicians.offer.accepted",
            entity="technician_service_offer",
            entity_id=str(offer.public_id),
            user=user,
            company=offer.service_request.requester_company,
            payload={"assignment_id": str(assignment.public_id)},
        )
        return assignment

    @staticmethod
    @transaction.atomic
    def reject_offer(*, user, offer):
        offer.status = TechnicianServiceOffer.Status.REJECTED
        offer.save(update_fields=["status", "updated_at"])
        AuditService.log(
            action="marketplace_technicians.offer.rejected",
            entity="technician_service_offer",
            entity_id=str(offer.public_id),
            user=user,
            company=offer.service_request.requester_company,
            payload={"status": offer.status},
        )
        try:
            marketplace_trigger_service = get_marketplace_allocation_trigger_service()
            marketplace_trigger_service.run_for_offer(offer=offer, user=user)
        except Exception:
            pass
        try:
            anomaly_trigger_service = get_anomaly_agent_trigger_service()
            anomaly_trigger_service.trigger_for_marketplace_request(service_request=offer.service_request, user=user)
        except Exception:
            pass
        return offer

    @staticmethod
    @transaction.atomic
    def withdraw_offer(*, user, offer):
        offer.status = TechnicianServiceOffer.Status.WITHDRAWN
        offer.save(update_fields=["status", "updated_at"])
        AuditService.log(
            action="marketplace_technicians.offer.withdrawn",
            entity="technician_service_offer",
            entity_id=str(offer.public_id),
            user=user,
            company=offer.service_request.requester_company,
            payload={"status": offer.status},
        )
        try:
            marketplace_trigger_service = get_marketplace_allocation_trigger_service()
            marketplace_trigger_service.run_for_offer(offer=offer, user=user)
        except Exception:
            pass
        try:
            anomaly_trigger_service = get_anomaly_agent_trigger_service()
            anomaly_trigger_service.trigger_for_marketplace_request(service_request=offer.service_request, user=user)
        except Exception:
            pass
        return offer


class TechnicianAssignmentService:
    @staticmethod
    def ensure_related_service_order(*, service_request, technician_profile):
        if service_request.related_service_order_id:
            return service_request.related_service_order
        related_client = service_request.related_client or getattr(service_request.related_site, "maintenance_client", None)
        if related_client is None or service_request.related_site is None:
            return None
        order = ServiceOrderService.create_service_order(
            user=technician_profile.user,
            validated_data={
                "client": related_client,
                "operational_site": service_request.related_site,
                "asset": service_request.related_asset,
                "maintenance_type": (
                    ServiceOrder.MaintenanceType.CORRECTIVE
                    if service_request.service_type in {
                        TechnicianServiceRequest.ServiceType.MAINTENANCE,
                        TechnicianServiceRequest.ServiceType.EMERGENCY,
                    }
                    else ServiceOrder.MaintenanceType.INSPECTION
                ),
                "priority": (
                    ServiceOrder.Priority.URGENT
                    if service_request.priority == TechnicianServiceRequest.Priority.URGENT
                    else ServiceOrder.Priority.HIGH
                    if service_request.priority == TechnicianServiceRequest.Priority.HIGH
                    else ServiceOrder.Priority.MEDIUM
                ),
                "status": ServiceOrder.Status.OPEN,
                "source": ServiceOrder.Source.MANUAL,
                "title": service_request.title,
                "description": service_request.description,
                "requested_by": service_request.requester_user.display_name
                if service_request.requester_user
                else service_request.requester_company.name
                if service_request.requester_company
                else "Marketplace",
                "assigned_to": technician_profile.user,
            },
        )
        service_request.related_service_order = order
        service_request.save(update_fields=["related_service_order", "updated_at"])
        return order

    @staticmethod
    @transaction.atomic
    def assign(*, service_request, technician_profile, service_offer=None, notes=""):
        assignment, created = TechnicianAssignment.objects.get_or_create(
            technician_service_request=service_request,
            technician_profile=technician_profile,
            defaults={
                "assignment_status": TechnicianAssignment.AssignmentStatus.ASSIGNED,
                "service_offer": service_offer,
                "notes": notes,
            },
        )
        if not created:
            if service_offer is not None and assignment.service_offer_id != service_offer.id:
                assignment.service_offer = service_offer
            if notes:
                assignment.notes = notes
            assignment.save(update_fields=["service_offer", "notes", "updated_at"])
        if created:
            TechnicianAssignmentService.ensure_related_service_order(
                service_request=service_request,
                technician_profile=technician_profile,
            )
            assignment.notes = notes
            service_request.status = service_request.Status.ASSIGNED
            service_request.save(update_fields=["status", "updated_at"])
            TechnicianMatchingRecord.objects.update_or_create(
                technician_service_request=service_request,
                technician_profile=technician_profile,
                defaults=TechnicianMatchingService.build_record_defaults(
                    technician_profile=technician_profile,
                    service_request=service_request,
                    status=TechnicianMatchingRecord.Status.ACCEPTED,
                ),
            )
            try:
                target_date = service_request.requested_date.date() if service_request.requested_date else timezone.localdate()
                scheduling_trigger_service = get_scheduling_agent_trigger_service()
                scheduling_trigger_service.run_day_analysis(
                    company=service_request.requester_company,
                    site=service_request.related_site,
                    target_date=target_date,
                    trigger_type="event",
                    trigger_reference=f"date:{target_date.isoformat()}",
                )
            except Exception:
                pass
        try:
            marketplace_trigger_service = get_marketplace_allocation_trigger_service()
            marketplace_trigger_service.run_for_assignment(assignment=assignment, user=technician_profile.user)
        except Exception:
            pass
        try:
            anomaly_trigger_service = get_anomaly_agent_trigger_service()
            anomaly_trigger_service.trigger_for_marketplace_assignment(assignment=assignment, user=technician_profile.user)
        except Exception:
            pass
        return assignment

    @staticmethod
    def transition_status(*, assignment, status):
        assignment.assignment_status = status
        now = timezone.now()
        related_service_order = assignment.technician_service_request.related_service_order
        if status == TechnicianAssignment.AssignmentStatus.ACCEPTED and not assignment.accepted_at:
            assignment.accepted_at = now
        if status == TechnicianAssignment.AssignmentStatus.DECLINED and not assignment.declined_at:
            assignment.declined_at = now
        if status == TechnicianAssignment.AssignmentStatus.IN_PROGRESS and not assignment.started_at:
            assignment.started_at = now
            assignment.technician_service_request.status = assignment.technician_service_request.Status.IN_PROGRESS
            assignment.technician_service_request.save(update_fields=["status", "updated_at"])
            if related_service_order is not None and related_service_order.status != ServiceOrder.Status.IN_PROGRESS:
                ServiceOrderService.update_service_order(
                    service_order=related_service_order,
                    validated_data={"status": ServiceOrder.Status.IN_PROGRESS},
                    user=assignment.technician_profile.user,
                )
        if status == TechnicianAssignment.AssignmentStatus.COMPLETED and not assignment.completed_at:
            assignment.completed_at = now
            assignment.technician_service_request.status = assignment.technician_service_request.Status.COMPLETED
            assignment.technician_service_request.save(update_fields=["status", "updated_at"])
            if related_service_order is not None and related_service_order.status != ServiceOrder.Status.COMPLETED:
                ServiceOrderService.update_service_order(
                    service_order=related_service_order,
                    validated_data={"status": ServiceOrder.Status.COMPLETED},
                    user=assignment.technician_profile.user,
                )
            technician_profile = assignment.technician_profile
            technician_profile.completed_jobs_count = technician_profile.assignments.filter(
                assignment_status=TechnicianAssignment.AssignmentStatus.COMPLETED
            ).count()
            technician_profile.save(update_fields=["completed_jobs_count", "updated_at"])
        assignment.save()
        try:
            service_request = assignment.technician_service_request
            target_date = service_request.requested_date.date() if service_request.requested_date else timezone.localdate()
            scheduling_trigger_service = get_scheduling_agent_trigger_service()
            scheduling_trigger_service.run_day_analysis(
                company=service_request.requester_company,
                site=service_request.related_site,
                target_date=target_date,
                trigger_type="event",
                trigger_reference=f"date:{target_date.isoformat()}",
            )
        except Exception:
            pass
        try:
            marketplace_trigger_service = get_marketplace_allocation_trigger_service()
            marketplace_trigger_service.run_for_assignment(assignment=assignment, user=assignment.technician_profile.user)
        except Exception:
            pass
        try:
            anomaly_trigger_service = get_anomaly_agent_trigger_service()
            anomaly_trigger_service.trigger_for_marketplace_assignment(assignment=assignment, user=assignment.technician_profile.user)
        except Exception:
            pass
        return assignment


class TechnicianReviewService:
    @staticmethod
    def refresh_rating(*, technician_profile):
        aggregation = technician_profile.reviews.filter(status=TechnicianReview.Status.PUBLISHED).aggregate(avg=Avg("rating"))
        technician_profile.rating_average = aggregation["avg"] or 0
        technician_profile.completed_jobs_count = technician_profile.assignments.filter(
            assignment_status=TechnicianAssignment.AssignmentStatus.COMPLETED
        ).count()
        technician_profile.save(update_fields=["rating_average", "completed_jobs_count", "updated_at"])
        return technician_profile

    @staticmethod
    def create_review(*, user, validated_data):
        review = TechnicianReview.objects.create(**validated_data)
        TechnicianReviewService.refresh_rating(technician_profile=review.technician_profile)
        AuditService.log(
            action="marketplace_technicians.review.created",
            entity="technician_review",
            entity_id=str(review.public_id),
            user=user,
            company=review.reviewer_company,
            payload={"rating": review.rating, "status": review.status},
        )
        return review


class TechnicianWorkReportService:
    @staticmethod
    def sync_labor_minutes(*, work_report):
        delta = work_report.ended_at - work_report.started_at
        work_report.labor_minutes = max(int(delta.total_seconds() // 60), 0)
        work_report.save(update_fields=["labor_minutes", "updated_at"])
        return work_report


class CompensationService:
    @staticmethod
    def default_net_amount(*, gross_amount, platform_fee):
        return Decimal(gross_amount) - Decimal(platform_fee or 0)

    @staticmethod
    def create_or_update(*, validated_data):
        if not validated_data.get("net_amount"):
            validated_data["net_amount"] = CompensationService.default_net_amount(
                gross_amount=validated_data["gross_amount"],
                platform_fee=validated_data.get("platform_fee", 0),
            )
        return validated_data
