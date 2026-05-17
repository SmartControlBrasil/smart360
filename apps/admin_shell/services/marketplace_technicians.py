from django.db.models import Avg, Count

from apps.marketplace_technicians.models import (
    TechnicianAssignment,
    TechnicianMatchingRecord,
    TechnicianProfile,
    TechnicianReview,
    TechnicianServiceOffer,
    TechnicianServiceRequest,
)
from apps.marketplace_technicians.services.access import MarketplaceAccessService


def _apply_company_site_filters(queryset, filters, *, company_field, site_field):
    if filters.get("company"):
        queryset = queryset.filter(**{company_field: filters["company"]})
    if filters.get("site") and site_field:
        queryset = queryset.filter(**{site_field: filters["site"]})
    return queryset


def _request_filters(queryset, filters):
    if filters.get("status"):
        queryset = queryset.filter(status=filters["status"])
    if filters.get("priority"):
        queryset = queryset.filter(priority=filters["priority"])
    queryset = _apply_company_site_filters(
        queryset,
        filters,
        company_field="requester_company__slug",
        site_field="related_site__code",
    )
    return queryset


def get_marketplace_dashboard_context(user):
    requests = MarketplaceAccessService.scope_requests_queryset(
        user,
        TechnicianServiceRequest.objects.select_related(
            "requester_company",
            "related_site",
            "related_asset",
        ),
    )
    assignments = MarketplaceAccessService.scope_assignments_queryset(
        user,
        TechnicianAssignment.objects.select_related(
            "technician_service_request",
            "technician_profile",
            "service_offer",
        ),
    )
    technicians = MarketplaceAccessService.scope_profiles_queryset(
        user,
        TechnicianProfile.objects.prefetch_related("skill_assignments__skill"),
    )
    reviews = MarketplaceAccessService.scope_reviews_queryset(
        user,
        TechnicianReview.objects.filter(status=TechnicianReview.Status.PUBLISHED),
    )
    matching_records = MarketplaceAccessService.scope_matching_queryset(
        user,
        TechnicianMatchingRecord.objects.select_related(
            "technician_service_request",
            "technician_service_request__requester_company",
            "technician_profile",
        ),
    )

    return {
        "marketplace_kpis": [
            {
                "label": "Solicitacoes abertas",
                "value": requests.filter(
                    status__in=[
                        TechnicianServiceRequest.Status.OPEN,
                        TechnicianServiceRequest.Status.MATCHING,
                        TechnicianServiceRequest.Status.OFFERS_RECEIVED,
                    ]
                ).count(),
                "tone": "indigo",
            },
            {
                "label": "Servicos em execucao",
                "value": assignments.filter(
                    assignment_status=TechnicianAssignment.AssignmentStatus.IN_PROGRESS,
                ).count(),
                "tone": "emerald",
            },
            {
                "label": "Servicos concluidos",
                "value": assignments.filter(
                    assignment_status=TechnicianAssignment.AssignmentStatus.COMPLETED,
                ).count(),
                "tone": "sky",
            },
            {
                "label": "Tecnicos ativos",
                "value": technicians.filter(
                    is_active=True,
                    marketplace_status=TechnicianProfile.MarketplaceStatus.AVAILABLE,
                ).count(),
                "tone": "amber",
            },
            {
                "label": "Media de avaliacao",
                "value": round(reviews.aggregate(avg=Avg("rating"))["avg"] or 0, 1),
                "tone": "violet",
            },
        ],
        "request_cards": requests.order_by("-created_at")[:6],
        "matching_highlights": matching_records.order_by("ranking_position", "-match_score")[:8],
        "recent_assignments": assignments.order_by("-updated_at")[:8],
        "top_technicians": technicians.order_by("-rating_average", "-completed_jobs_count")[:6],
        "page_actions": [
            {"label": "Service Requests", "route_name": "admin-shell:marketplace-technicians-requests"},
            {"label": "Matching", "route_name": "admin-shell:marketplace-technicians-matching"},
            {"label": "Offers", "route_name": "admin-shell:marketplace-technicians-offers"},
            {"label": "Technicians", "route_name": "admin-shell:marketplace-technicians-technicians"},
            {"label": "Assignments", "route_name": "admin-shell:marketplace-technicians-assignments"},
            {"label": "Reviews", "route_name": "admin-shell:marketplace-technicians-reviews"},
        ],
    }


def get_service_request_listing_context(user, filters=None):
    filters = filters or {}
    queryset = MarketplaceAccessService.scope_requests_queryset(
        user,
        TechnicianServiceRequest.objects.select_related(
            "requester_company",
            "related_site",
            "related_asset",
        ).annotate(offers_received=Count("offers", distinct=True)),
    )
    queryset = _request_filters(queryset, filters)
    return {
        "service_requests": queryset.order_by("-created_at"),
        "filters": filters,
        "request_kpis": [
            {
                "label": "Abertas",
                "value": queryset.filter(status=TechnicianServiceRequest.Status.OPEN).count(),
                "tone": "indigo",
            },
            {
                "label": "Com ofertas",
                "value": queryset.filter(status=TechnicianServiceRequest.Status.OFFERS_RECEIVED).count(),
                "tone": "sky",
            },
            {
                "label": "Atribuidas",
                "value": queryset.filter(status=TechnicianServiceRequest.Status.ASSIGNED).count(),
                "tone": "emerald",
            },
            {
                "label": "Urgentes",
                "value": queryset.filter(priority=TechnicianServiceRequest.Priority.URGENT).count(),
                "tone": "rose",
            },
        ],
    }


def get_matching_listing_context(user, filters=None):
    filters = filters or {}
    request_queryset = MarketplaceAccessService.scope_requests_queryset(
        user,
        TechnicianServiceRequest.objects.select_related(
            "requester_company",
            "related_site",
            "related_asset",
        ),
    )
    if filters.get("status"):
        request_queryset = request_queryset.filter(status=filters["status"])
    request_queryset = _apply_company_site_filters(
        request_queryset,
        filters,
        company_field="requester_company__slug",
        site_field="related_site__code",
    )
    matching_queryset = MarketplaceAccessService.scope_matching_queryset(
        user,
        TechnicianMatchingRecord.objects.select_related(
            "technician_service_request",
            "technician_service_request__requester_company",
            "technician_service_request__related_site",
            "technician_profile",
        ),
    )
    matching_queryset = _apply_company_site_filters(
        matching_queryset,
        filters,
        company_field="technician_service_request__requester_company__slug",
        site_field="technician_service_request__related_site__code",
    )
    if filters.get("request"):
        matching_queryset = matching_queryset.filter(
            technician_service_request__public_id=filters["request"]
        )
    return {
        "matching_records": matching_queryset.order_by("ranking_position", "-match_score"),
        "matching_requests": request_queryset.order_by("-created_at")[:20],
        "filters": filters,
        "matching_kpis": [
            {
                "label": "Solicitacoes em matching",
                "value": request_queryset.filter(status=TechnicianServiceRequest.Status.MATCHING).count(),
                "tone": "indigo",
            },
            {
                "label": "Tecnicos sugeridos",
                "value": matching_queryset.count(),
                "tone": "sky",
            },
            {
                "label": "Top score medio",
                "value": round(matching_queryset.aggregate(avg=Avg("match_score"))["avg"] or 0, 1),
                "tone": "emerald",
            },
            {
                "label": "Scores >= 80",
                "value": matching_queryset.filter(match_score__gte=80).count(),
                "tone": "violet",
            },
        ],
    }


def get_service_offer_listing_context(user, filters=None):
    filters = filters or {}
    queryset = MarketplaceAccessService.scope_offers_queryset(
        user,
        TechnicianServiceOffer.objects.select_related(
            "service_request",
            "service_request__requester_company",
            "service_request__related_site",
            "technician_profile",
        ),
    )
    if filters.get("status"):
        queryset = queryset.filter(status=filters["status"])
    queryset = _apply_company_site_filters(
        queryset,
        filters,
        company_field="service_request__requester_company__slug",
        site_field="service_request__related_site__code",
    )
    return {
        "service_offers": queryset.order_by("-created_at"),
        "filters": filters,
    }


def get_technician_listing_context(user, filters=None):
    filters = filters or {}
    queryset = MarketplaceAccessService.scope_profiles_queryset(
        user,
        TechnicianProfile.objects.annotate(
            specialties_count=Count("skill_assignments", distinct=True),
            reviews_count=Count("reviews", distinct=True),
        ).prefetch_related("skill_assignments__skill"),
    )
    if filters.get("status"):
        queryset = queryset.filter(marketplace_status=filters["status"])
    return {
        "technicians": queryset.order_by("-rating_average", "-completed_jobs_count", "display_name"),
        "filters": filters,
    }


def get_technician_detail_context(user, public_id):
    technician = MarketplaceAccessService.scope_profiles_queryset(
        user,
        TechnicianProfile.objects.select_related("user", "company").prefetch_related(
            "skill_assignments__skill",
            "service_regions__service_region",
            "assignments__technician_service_request",
            "reviews",
        ),
    ).filter(public_id=public_id).first()
    if technician is None:
        return None
    return {
        "technician": technician,
        "specialties": technician.skill_assignments.all(),
        "service_regions": technician.service_regions.all(),
        "assignments": technician.assignments.order_by("-updated_at")[:12],
        "reviews": technician.reviews.order_by("-created_at")[:12],
    }


def get_assignment_listing_context(user, filters=None):
    filters = filters or {}
    queryset = MarketplaceAccessService.scope_assignments_queryset(
        user,
        TechnicianAssignment.objects.select_related(
            "technician_service_request",
            "technician_service_request__requester_company",
            "technician_service_request__related_site",
            "technician_profile",
            "service_offer",
        ),
    )
    if filters.get("status"):
        queryset = queryset.filter(assignment_status=filters["status"])
    queryset = _apply_company_site_filters(
        queryset,
        filters,
        company_field="technician_service_request__requester_company__slug",
        site_field="technician_service_request__related_site__code",
    )
    return {
        "assignments": queryset.order_by("-assigned_at"),
        "filters": filters,
    }


def get_review_listing_context(user, filters=None):
    filters = filters or {}
    queryset = MarketplaceAccessService.scope_reviews_queryset(
        user,
        TechnicianReview.objects.select_related(
            "assignment",
            "assignment__technician_service_request",
            "assignment__technician_service_request__requester_company",
            "technician_profile",
            "reviewer_company",
        ),
    )
    queryset = _apply_company_site_filters(
        queryset,
        filters,
        company_field="assignment__technician_service_request__requester_company__slug",
        site_field="assignment__technician_service_request__related_site__code",
    )
    return {
        "reviews": queryset.order_by("-created_at"),
        "filters": filters,
    }
